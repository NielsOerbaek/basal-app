import json
import logging

import resend
from django.conf import settings
from django.db.models import F
from django.http import FileResponse, JsonResponse, QueryDict, StreamingHttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import DetailView, ListView

from apps.bulk_email.models import BulkEmail, BulkEmailAttachment
from apps.bulk_email.services import (
    VARIABLE_NAMES,
    find_missing_variables,
    render_for_school,
    resolve_recipients,
    send_to_school,
)
from apps.core.decorators import staff_required
from apps.emails.services import EMAIL_FOOTER, check_email_domain_allowed
from apps.schools.mixins import SchoolFilterMixin
from apps.schools.models import Person, School

logger = logging.getLogger(__name__)


@method_decorator(staff_required, name="dispatch")
class BulkEmailListView(ListView):
    model = BulkEmail
    template_name = "bulk_email/bulk_email_list.html"
    context_object_name = "campaigns"

    def get_queryset(self):
        return BulkEmail.objects.prefetch_related("recipients").order_by(
            F("sent_at").asc(nulls_first=True),
            "-created_at",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for campaign in context["campaigns"]:
            campaign.recipient_count = campaign.recipients.count()
            campaign.failure_count = campaign.recipients.filter(success=False).count()
        return context


@method_decorator(staff_required, name="dispatch")
class BulkEmailDetailView(DetailView):
    model = BulkEmail
    template_name = "bulk_email/bulk_email_detail.html"
    context_object_name = "campaign"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        campaign = self.object
        context["recipients"] = campaign.recipients.select_related("school", "person").order_by(
            "success", "school__name"
        )
        context["sent_count"] = campaign.recipients.filter(success=True).count()
        context["failed_count"] = campaign.recipients.filter(success=False).count()
        context["filter_summary"] = campaign.get_filter_summary_display()
        return context


@method_decorator(staff_required, name="dispatch")
class BulkEmailCreateView(SchoolFilterMixin, View):
    def get(self, request):
        from apps.bulk_email.forms import BulkEmailComposeForm

        initial = {}
        copy_from_pk = request.GET.get("copy_from")
        copy_source = None
        if copy_from_pk:
            try:
                copy_source = BulkEmail.objects.get(pk=copy_from_pk)
                initial["subject"] = request.GET.get("subject", copy_source.subject)
                initial["body_html"] = copy_source.body_html
                initial["recipient_type"] = request.GET.get("recipient_type", copy_source.recipient_type)
            except BulkEmail.DoesNotExist:
                pass

        form = BulkEmailComposeForm(initial=initial)
        schools = list(self.get_school_filter_queryset())
        filter_context = self.get_filter_context()

        context = {
            "form": form,
            "schools": schools[:200],
            "total_matched": len(schools),
            "variable_names": VARIABLE_NAMES,
            "copy_source": copy_source,
            **filter_context,
        }
        return render(request, "bulk_email/bulk_email_create.html", context)


@method_decorator(staff_required, name="dispatch")
class BulkEmailPreviewView(View):
    def post(self, request):
        try:
            payload = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        school_pk = payload.get("school_pk")
        subject = payload.get("subject", "")
        body_html = payload.get("body_html", "")
        recipient_type = payload.get("recipient_type", BulkEmail.KOORDINATOR)

        school = get_object_or_404(School, pk=school_pk)

        # Find the contact person based on recipient type
        person = None
        if recipient_type == BulkEmail.KOORDINATOR:
            person = school.people.filter(is_koordinator=True, email__isnull=False).exclude(email="").first()
        elif recipient_type == BulkEmail.OEKONOMISK_ANSVARLIG:
            person = school.people.filter(is_oekonomisk_ansvarlig=True, email__isnull=False).exclude(email="").first()
        if person is None:
            person = school.people.first()

        rendered_body = render_for_school(body_html, school, person)
        rendered_subject = render_for_school(subject, school, person)

        return render(
            request,
            "bulk_email/bulk_email_preview.html",
            {
                "subject": rendered_subject,
                "body_html": rendered_body,
                "school": school,
            },
        )


@method_decorator(staff_required, name="dispatch")
class BulkEmailDryRunView(View):
    def post(self, request):
        try:
            payload = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        recipient_type = payload.get("recipient_type", BulkEmail.KOORDINATOR)
        subject = payload.get("subject", "")
        body_html = payload.get("body_html", "")
        filter_params = payload.get("filter_params", {})

        # Build a fake request to use the mixin filter logic
        from urllib.parse import urlencode

        from django.http import QueryDict

        fake_qs = QueryDict(urlencode(filter_params))

        class _FakeRequest:
            GET = fake_qs

        # Use SchoolFilterMixin to resolve filtered schools
        class _FilterView(SchoolFilterMixin):
            request = _FakeRequest()

        view = _FilterView()
        schools = list(view.get_school_filter_queryset())

        pairs = resolve_recipients(schools, recipient_type)

        # Combined template for variable analysis
        combined = subject + " " + body_html
        warnings = find_missing_variables(combined, pairs)

        recipients_data = [
            {
                "school": school.name,
                "person": person.name,
                "email": person.email,
            }
            for school, person in pairs
        ]

        return JsonResponse(
            {
                "recipients": recipients_data,
                "total": len(recipients_data),
                "skipped": len(schools) - len(pairs),
                "warnings": warnings,
            }
        )


@method_decorator(staff_required, name="dispatch")
class BulkEmailSendView(SchoolFilterMixin, View):
    def post(self, request):
        data = json.loads(request.body)

        subject = data.get("subject", "")
        body_html = data.get("body_html", "")
        recipient_type = data.get("recipient_type", BulkEmail.KOORDINATOR)
        filter_params = data.get("filter_params", {})
        attachment_pks = data.get("attachment_pks", [])

        # Test email path: send directly to one address without creating a BulkEmail record
        test_email = data.get("test_email")
        if test_email:
            test_school_pk = data.get("test_school_pk")
            if test_school_pk:
                try:
                    school = School.objects.prefetch_related("people").get(pk=test_school_pk)
                    person = school.people.filter(email__gt="").first()
                except School.DoesNotExist:
                    school = School(name="Test", signup_token="", signup_password="")
                    person = None
            else:
                school = School(name="Test", signup_token="", signup_password="")
                person = None

            fake_person = Person(name="Test", email=test_email)
            rendered_subject = render_for_school(subject, school, person or fake_person)
            rendered_body = render_for_school(body_html, school, person or fake_person) + EMAIL_FOOTER

            def test_stream():
                success = True
                error = ""
                if not check_email_domain_allowed(test_email):
                    success = False
                    error = "[BLOCKED] Domain not in EMAIL_ALLOWED_DOMAINS"
                elif not getattr(settings, "RESEND_API_KEY", None):
                    logger.info(f"[TEST EMAIL] DEV MODE — To: {test_email}")
                else:
                    try:
                        resend.api_key = settings.RESEND_API_KEY
                        resend.Emails.send(
                            {
                                "from": settings.DEFAULT_FROM_EMAIL,
                                "to": [test_email],
                                "subject": rendered_subject,
                                "html": rendered_body,
                            }
                        )
                    except Exception as e:
                        success = False
                        error = str(e)[:200]
                yield f"data: {json.dumps({'type': 'start', 'total': 1, 'skipped': 0})}\n\n"
                yield f"data: {json.dumps({'type': 'progress', 'n': 1, 'total': 1, 'school': school.name, 'email': test_email, 'success': success, 'error': error})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'sent': 1 if success else 0, 'failed': 0 if success else 1, 'skipped': 0, 'detail_url': ''})}\n\n"

            response = StreamingHttpResponse(test_stream(), content_type="text/event-stream")
            response["Cache-Control"] = "no-cache"
            response["X-Accel-Buffering"] = "no"
            return response

        # Normal send path
        from urllib.parse import urlencode

        fake_get = QueryDict(urlencode(filter_params), mutable=True)
        original_get = request.GET
        request.GET = fake_get
        schools = list(self.get_school_filter_queryset())
        request.GET = original_get

        school_person_pairs = resolve_recipients(schools, recipient_type)

        campaign = BulkEmail.objects.create(
            subject=subject,
            body_html=body_html,
            recipient_type=recipient_type,
            filter_params=filter_params,
            sent_by=request.user,
        )

        if attachment_pks:
            BulkEmailAttachment.objects.filter(pk__in=attachment_pks).update(bulk_email=campaign)

        def event_stream():
            sent = 0
            failed = 0
            skipped = len(schools) - len(school_person_pairs)

            yield f"data: {json.dumps({'type': 'start', 'total': len(school_person_pairs), 'skipped': skipped})}\n\n"

            for n, (school, person) in enumerate(school_person_pairs, start=1):
                recipient = send_to_school(campaign, school, person)
                if recipient.success:
                    sent += 1
                else:
                    failed += 1
                event = {
                    "type": "progress",
                    "n": n,
                    "total": len(school_person_pairs),
                    "school": school.name,
                    "email": recipient.email,
                    "success": recipient.success,
                    "error": recipient.error_message if not recipient.success else "",
                }
                yield f"data: {json.dumps(event)}\n\n"

            campaign.sent_at = timezone.now()
            campaign.save(update_fields=["sent_at"])

            detail_url = reverse("bulk_email:detail", args=[campaign.pk])
            yield f"data: {json.dumps({'type': 'done', 'sent': sent, 'failed': failed, 'skipped': skipped, 'detail_url': detail_url})}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


@method_decorator(staff_required, name="dispatch")
class BulkEmailAttachmentUploadView(View):
    def post(self, request):
        f = request.FILES.get("file")
        if not f:
            return JsonResponse({"error": "No file"}, status=400)
        attachment = BulkEmailAttachment.objects.create(
            filename=f.name,
            file=f,
        )
        return JsonResponse({"pk": attachment.pk, "filename": attachment.filename})


@method_decorator(staff_required, name="dispatch")
class BulkEmailAttachmentDownloadView(View):
    def get(self, request, pk):
        attachment = get_object_or_404(BulkEmailAttachment, pk=pk)
        return FileResponse(attachment.file.open("rb"), as_attachment=True, filename=attachment.filename)
