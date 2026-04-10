import json
import logging
import time

import resend
from django.conf import settings
from django.db.models import F
from django.http import FileResponse, JsonResponse, QueryDict, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import DetailView, ListView

from apps.bulk_email.models import BulkEmail, BulkEmailAttachment
from apps.bulk_email.services import (
    VARIABLE_NAMES,
    find_missing_variables,
    make_urls_absolute,
    render_for_school,
    resolve_recipients,
    send_to_school,
)
from apps.core.decorators import full_admin_required
from apps.emails.services import DEFAULT_REPLY_TO, check_email_domain_allowed
from apps.schools.mixins import SchoolFilterMixin
from apps.schools.models import Person, School

logger = logging.getLogger(__name__)


@method_decorator(full_admin_required, name="dispatch")
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


@method_decorator(full_admin_required, name="dispatch")
class BulkEmailDetailView(DetailView):
    model = BulkEmail
    template_name = "bulk_email/bulk_email_detail.html"
    context_object_name = "campaign"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        campaign = self.object
        recipients = list(campaign.recipients.select_related("school", "person").order_by("success", "school__name"))

        # Collect person bounce status (for recipients where person still exists)
        person_pks = [r.person_id for r in recipients if r.person_id]
        bounced_person_pks = set(
            Person.objects.filter(pk__in=person_pks, email_bounced_at__isnull=False).values_list("pk", flat=True)
        )

        # Annotate recipients with bounce info
        bounced_count = 0
        schools_with_bounces = {}  # school_id -> [has_non_bounced]
        for r in recipients:
            # bounced_at on the recipient itself is authoritative (survives person deletion)
            # Fall back to Person.email_bounced_at only for legacy recipients (no resend done)
            if r.resent_to:
                # Resend was attempted — only bounced_at matters (set again by webhook if re-bounced)
                r.is_bounced = bool(r.bounced_at)
            else:
                r.is_bounced = bool(r.bounced_at) or (r.person_id in bounced_person_pks)

            # Detect if contact email was changed externally (not via resend)
            r.email_changed = (
                r.person and r.person.email and r.person.email.lower() != r.email.lower() and not r.resent_to
            )

            if r.resent_to:
                contact_was_updated = r.person and r.person.email == r.resent_to
                if contact_was_updated:
                    # Contact email was changed — resolved only if not re-bounced
                    r.is_resolved = not r.is_bounced
                else:
                    # One-off resend — resolved for this campaign (can't track re-bounces)
                    r.is_resolved = True
            else:
                r.is_resolved = False

            # Count as unresolved if bounced OR email changed but not resent
            r.needs_action = (r.is_bounced and not r.is_resolved) or r.email_changed
            if r.needs_action:
                bounced_count += 1

            # Track per-school bounce status
            if r.school_id and r.success:
                if r.school_id not in schools_with_bounces:
                    schools_with_bounces[r.school_id] = {
                        "all_bounced": True,
                        "name": r.school.name if r.school else "—",
                    }
                if not r.needs_action:
                    schools_with_bounces[r.school_id]["all_bounced"] = False

        missing_schools = sorted(s["name"] for s in schools_with_bounces.values() if s["all_bounced"])

        context["recipients"] = recipients
        context["sent_count"] = sum(1 for r in recipients if r.success)
        context["failed_count"] = sum(1 for r in recipients if not r.success)
        context["bounced_count"] = bounced_count
        context["schools_missing"] = len(missing_schools)
        context["missing_school_names"] = missing_schools
        context["filter_summary"] = campaign.get_filter_summary_display()
        return context


@method_decorator(full_admin_required, name="dispatch")
class BulkEmailResendView(View):
    """Resend a bulk email to a new address for a specific recipient."""

    def post(self, request, recipient_pk):
        from apps.bulk_email.models import BulkEmailRecipient

        recipient = get_object_or_404(
            BulkEmailRecipient.objects.select_related("bulk_email", "school", "person"), pk=recipient_pk
        )
        new_email = request.POST.get("new_email", "").strip()
        update_contact = request.POST.get("update_contact") == "1"

        if not new_email:
            return JsonResponse({"error": "E-mailadresse mangler"}, status=400)

        campaign = recipient.bulk_email
        school = recipient.school
        person = recipient.person

        # Render the email content
        subject = render_for_school(campaign.subject, school, person)
        body_html = make_urls_absolute(render_for_school(campaign.body_html, school, person))

        # Domain check
        if not check_email_domain_allowed(new_email):
            return JsonResponse({"error": "Domænet er ikke tilladt"}, status=400)

        # Dev mode guard
        if not getattr(settings, "RESEND_API_KEY", None):
            logger.info(f"[RESEND] DEV MODE — To: {new_email} Subject: {subject}")
            recipient.resent_to = new_email
            recipient.resent_at = timezone.now()
            recipient.bounced_at = None
            recipient.save(update_fields=["resent_to", "resent_at", "bounced_at"])
            if update_contact and person:
                person.email = new_email
                person.email_bounced_at = None
                person.save(update_fields=["email", "email_bounced_at"])
            return JsonResponse({"success": True, "email": new_email, "contact_updated": update_contact})

        try:
            # Load attachments
            attachments = []
            for att in campaign.attachments.all():
                with att.file.open("rb") as f:
                    attachments.append({"filename": att.filename, "content": list(f.read())})

            params = {
                "from": settings.DEFAULT_FROM_EMAIL,
                "to": [new_email],
                "reply_to": DEFAULT_REPLY_TO,
                "subject": subject,
                "html": body_html,
            }
            if attachments:
                params["attachments"] = attachments

            resend.api_key = settings.RESEND_API_KEY
            resend.Emails.send(params)

            recipient.resent_to = new_email
            recipient.resent_at = timezone.now()
            recipient.bounced_at = None
            recipient.save(update_fields=["resent_to", "resent_at", "bounced_at"])

            if update_contact and person:
                person.email = new_email
                person.email_bounced_at = None
                person.save(update_fields=["email", "email_bounced_at"])

            return JsonResponse({"success": True, "email": new_email, "contact_updated": update_contact})

        except (ConnectionError, OSError) as e:
            logger.error(f"[RESEND] Network error resending to {new_email}: {e}")
            return JsonResponse(
                {"error": "Kunne ikke oprette forbindelse til e-mailserveren. Prøv igen om et minut."}, status=503
            )
        except Exception as e:
            logger.error(f"[RESEND] Failed to resend to {new_email}: {e}")
            return JsonResponse({"error": str(e)[:500]}, status=500)


@method_decorator(full_admin_required, name="dispatch")
class BulkEmailCreateView(SchoolFilterMixin, View):
    def get(self, request):
        from apps.bulk_email.forms import BulkEmailComposeForm

        initial = {}
        copy_source = None
        draft = None

        # Load draft for editing
        draft_pk = request.GET.get("draft")
        if draft_pk:
            try:
                draft = BulkEmail.objects.get(pk=draft_pk, sent_at__isnull=True)
                initial["subject"] = draft.subject
                initial["body_html"] = draft.body_html
                initial["recipient_type"] = draft.recipient_type
            except BulkEmail.DoesNotExist:
                draft = None

        # Copy from existing campaign
        copy_from_pk = request.GET.get("copy_from")
        if not draft and copy_from_pk:
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

        # Pre-load draft attachments
        draft_attachments = []
        if draft:
            draft_attachments = list(draft.attachments.values("pk", "filename"))

        context = {
            "form": form,
            "schools": schools[:5000],
            "total_matched": len(schools),
            "variable_names": VARIABLE_NAMES,
            "copy_source": copy_source,
            "draft": draft,
            "draft_attachments_json": json.dumps(draft_attachments),
            **filter_context,
        }
        return render(request, "bulk_email/bulk_email_create.html", context)


@method_decorator(full_admin_required, name="dispatch")
class BulkEmailDraftSaveView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        draft_pk = data.get("draft_pk")
        name = data.get("name", "")
        subject = data.get("subject", "")
        body_html = data.get("body_html", "")
        recipient_type = data.get("recipient_type", BulkEmail.KOORDINATOR)
        filter_params = data.get("filter_params", {})
        attachment_pks = data.get("attachment_pks", [])

        if draft_pk:
            try:
                draft = BulkEmail.objects.get(pk=draft_pk, sent_at__isnull=True)
                # Don't update interrupted sends
                if draft.recipients.exists():
                    return JsonResponse({"error": "Cannot edit a campaign that has started sending"}, status=409)
                draft.name = name
                draft.subject = subject
                draft.body_html = body_html
                draft.recipient_type = recipient_type
                draft.filter_params = filter_params
                draft.save()
            except BulkEmail.DoesNotExist:
                return JsonResponse({"error": "Draft not found"}, status=404)
        else:
            draft = BulkEmail.objects.create(
                name=name or "(unavngivet)",
                subject=subject,
                body_html=body_html,
                recipient_type=recipient_type,
                filter_params=filter_params,
            )

        # Link attachments
        if attachment_pks:
            BulkEmailAttachment.objects.filter(pk__in=attachment_pks, bulk_email__isnull=True).update(bulk_email=draft)

        return JsonResponse({"pk": draft.pk, "saved": True})


@method_decorator(full_admin_required, name="dispatch")
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

        # Find the contact person based on recipient type (use first match for preview)
        person = None
        people = school.people.exclude(email="").filter(email__isnull=False)
        if recipient_type == BulkEmail.KOORDINATOR:
            person = people.filter(is_koordinator=True).first()
        elif recipient_type == BulkEmail.OEKONOMISK_ANSVARLIG:
            person = people.filter(is_oekonomisk_ansvarlig=True).first()
        elif recipient_type == BulkEmail.BEGGE:
            person = people.filter(is_koordinator=True).first() or people.filter(is_oekonomisk_ansvarlig=True).first()
        elif recipient_type == BulkEmail.FOERSTE_KONTAKT:
            person = people.first()
        elif recipient_type == BulkEmail.ALLE_KONTAKTER:
            person = people.first()
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


@method_decorator(full_admin_required, name="dispatch")
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
        fake_qs = QueryDict(mutable=True)
        for k, v in filter_params.items():
            if isinstance(v, list):
                fake_qs.setlist(k, [str(x) for x in v])
            else:
                fake_qs[k] = str(v)

        class _FakeRequest:
            GET = fake_qs

        # Use SchoolFilterMixin to resolve filtered schools
        class _FilterView(SchoolFilterMixin):
            request = _FakeRequest()

        view = _FilterView()
        schools = list(view.get_school_filter_queryset())

        pairs = resolve_recipients(schools, recipient_type)
        matched_school_pks = {school.pk for school, _person in pairs}

        # Combined template for variable analysis
        combined = subject + " " + body_html
        warnings = find_missing_variables(combined, pairs)

        recipients_data = [
            {
                "school": school.name,
                "person": person.name,
                "email": person.email,
                "kommune": school.kommune.name if school.kommune else "",
            }
            for school, person in pairs
        ]

        skipped_data = [
            {"school": school.name, "kommune": school.kommune.name if school.kommune else ""}
            for school in schools
            if school.pk not in matched_school_pks
        ]

        return JsonResponse(
            {
                "recipients": recipients_data,
                "total": len(recipients_data),
                "total_schools": len(schools),
                "schools_sending": len(matched_school_pks),
                "skipped": len(skipped_data),
                "skipped_schools": skipped_data,
                "warnings": warnings,
            }
        )


@method_decorator(full_admin_required, name="dispatch")
class BulkEmailSendView(SchoolFilterMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        name = data.get("name", "")
        subject = data.get("subject", "")
        body_html = data.get("body_html", "")
        recipient_type = data.get("recipient_type", BulkEmail.KOORDINATOR)
        filter_params = data.get("filter_params", {})
        attachment_pks = data.get("attachment_pks", [])

        # Double-send guard: reject if a similar campaign was created in the last 60 seconds
        test_email = data.get("test_email")
        if not test_email:
            from datetime import timedelta

            cutoff = timezone.now() - timedelta(seconds=60)
            if BulkEmail.objects.filter(
                subject=subject,
                recipient_type=recipient_type,
                filter_params=filter_params,
                sent_by=request.user,
                created_at__gte=cutoff,
            ).exists():
                return JsonResponse(
                    {"error": "En identisk udsendelse blev oprettet for nylig. Vent venligst."},
                    status=409,
                )

        # Test email path: send directly to one address without creating a BulkEmail record
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
            rendered_body = make_urls_absolute(render_for_school(body_html, school, person or fake_person))

            # Load attachments for test email
            test_attachments = []
            if attachment_pks:
                for att in BulkEmailAttachment.objects.filter(pk__in=attachment_pks):
                    with att.file.open("rb") as f:
                        test_attachments.append({"filename": att.filename, "content": list(f.read())})

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
                        params = {
                            "from": settings.DEFAULT_FROM_EMAIL,
                            "to": [test_email],
                            "reply_to": DEFAULT_REPLY_TO,
                            "subject": rendered_subject,
                            "html": rendered_body,
                        }
                        if test_attachments:
                            params["attachments"] = test_attachments
                        resend.Emails.send(params)
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
        fake_get = QueryDict(mutable=True)
        for k, v in filter_params.items():
            if isinstance(v, list):
                fake_get.setlist(k, [str(x) for x in v])
            else:
                fake_get[k] = str(v)
        original_get = request.GET
        request.GET = fake_get
        schools = list(self.get_school_filter_queryset())
        request.GET = original_get

        school_person_pairs = resolve_recipients(schools, recipient_type)

        # Use existing draft or create new campaign
        draft_pk = data.get("draft_pk")
        if draft_pk:
            try:
                campaign = BulkEmail.objects.get(pk=draft_pk, sent_at__isnull=True)
                if campaign.recipients.exists():
                    return JsonResponse({"error": "Cannot send an interrupted campaign"}, status=409)
                campaign.name = name
                campaign.subject = subject
                campaign.body_html = body_html
                campaign.recipient_type = recipient_type
                campaign.filter_params = filter_params
                campaign.sent_by = request.user
                campaign.save()
            except BulkEmail.DoesNotExist:
                return JsonResponse({"error": "Draft not found"}, status=404)
        else:
            campaign = BulkEmail.objects.create(
                name=name,
                subject=subject,
                body_html=body_html,
                recipient_type=recipient_type,
                filter_params=filter_params,
                sent_by=request.user,
            )

        if attachment_pks:
            BulkEmailAttachment.objects.filter(pk__in=attachment_pks).update(bulk_email=campaign)

        # Pre-load attachment data once before the streaming loop
        attachment_data = []
        for att in campaign.attachments.all():
            with att.file.open("rb") as f:
                attachment_data.append({"filename": att.filename, "content": list(f.read())})

        def event_stream():
            sent = 0
            failed = 0
            skipped = len(schools) - len(school_person_pairs)

            yield f"data: {json.dumps({'type': 'start', 'total': len(school_person_pairs), 'skipped': skipped})}\n\n"

            for n, (school, person) in enumerate(school_person_pairs, start=1):
                if n > 1:
                    time.sleep(0.25)
                recipient = send_to_school(campaign, school, person, attachment_data=attachment_data)
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


@method_decorator(full_admin_required, name="dispatch")
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


@method_decorator(full_admin_required, name="dispatch")
class BulkEmailAttachmentDownloadView(View):
    def get(self, request, pk):
        attachment = get_object_or_404(BulkEmailAttachment, pk=pk)
        return FileResponse(attachment.file.open("rb"), as_attachment=True, filename=attachment.filename)


@method_decorator(full_admin_required, name="dispatch")
class BulkEmailDeleteView(View):
    def post(self, request, pk):
        campaign = get_object_or_404(BulkEmail, pk=pk)
        # Delete attachment files from storage
        for att in campaign.attachments.all():
            att.file.delete(save=False)
        campaign.delete()
        return redirect("bulk_email:list")
