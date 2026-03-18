import json
import logging

from django.db.models import F
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import DetailView, ListView

from apps.bulk_email.models import BulkEmail, BulkEmailAttachment
from apps.bulk_email.services import find_missing_variables, render_for_school, resolve_recipients
from apps.core.decorators import staff_required
from apps.schools.mixins import SchoolFilterMixin
from apps.schools.models import School

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
class BulkEmailCreateView(View):
    def get(self, request):
        from django.http import HttpResponse

        return HttpResponse("create placeholder")


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
class BulkEmailSendView(View):
    def post(self, request):
        from django.http import HttpResponse

        return HttpResponse("send placeholder")


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
