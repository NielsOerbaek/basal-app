import logging

import resend
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from svix.webhooks import Webhook, WebhookVerificationError

logger = logging.getLogger(__name__)

BOUNCE_NOTIFICATION_RECIPIENT = "basal@sundkom.dk"


def lookup_email_owner(email):
    """Look up person and school associated with a bounced email address."""
    from apps.courses.models import CourseSignUp
    from apps.schools.models import Person, School

    results = []

    # Check Person (koordinator, økonomisk ansvarlig, etc.)
    for person in Person.objects.filter(email__iexact=email).select_related("school"):
        roles = []
        if person.is_koordinator:
            roles.append("koordinator")
        if person.is_oekonomisk_ansvarlig:
            roles.append("økonomiansvarlig")
        role_str = ", ".join(roles) if roles else "kontaktperson"
        results.append((person.name, person.school.name, role_str))

    # Check CourseSignUp (participant)
    for signup in CourseSignUp.objects.filter(participant_email__iexact=email).select_related("school", "course"):
        school_name = signup.school.name if signup.school else "ukendt skole"
        results.append((signup.participant_name, school_name, "kursustilmeldt"))

    # Check school billing email
    for school in School.objects.filter(fakturering_kontakt_email__iexact=email):
        results.append((school.fakturering_kontakt_navn or "faktureringsmodtager", school.name, "fakturering"))

    return results


def mark_email_bounced(email, at=None):
    """Mark all records matching this email address as bounced."""
    from apps.bulk_email.models import BulkEmailRecipient
    from apps.courses.models import CourseSignUp
    from apps.schools.models import Person, School

    now = at or timezone.now()
    Person.objects.filter(email__iexact=email, email_bounced_at__isnull=True).update(email_bounced_at=now)
    CourseSignUp.objects.filter(participant_email__iexact=email, email_bounced_at__isnull=True).update(
        email_bounced_at=now
    )
    School.objects.filter(fakturering_kontakt_email__iexact=email, fakturering_email_bounced_at__isnull=True).update(
        fakturering_email_bounced_at=now
    )
    BulkEmailRecipient.objects.filter(email__iexact=email, bounced_at__isnull=True, success=True).update(bounced_at=now)


@method_decorator(csrf_exempt, name="dispatch")
class ResendWebhookView(View):
    """
    Webhook endpoint for Resend email events.
    Sends a notification email when a bounce or complaint is received.

    Secured via svix signature verification using RESEND_WEBHOOK_SECRET.
    """

    def post(self, request):
        webhook_secret = getattr(settings, "RESEND_WEBHOOK_SECRET", None)
        if not webhook_secret:
            logger.error("RESEND_WEBHOOK_SECRET not configured")
            return JsonResponse({"error": "not configured"}, status=500)

        # Verify svix signature
        headers = {
            "svix-id": request.headers.get("svix-id", ""),
            "svix-timestamp": request.headers.get("svix-timestamp", ""),
            "svix-signature": request.headers.get("svix-signature", ""),
        }

        try:
            wh = Webhook(webhook_secret)
            payload = wh.verify(request.body, headers)
        except WebhookVerificationError:
            logger.warning("[WEBHOOK] Invalid signature")
            return JsonResponse({"error": "invalid signature"}, status=401)

        event_type = payload.get("type", "")

        if event_type not in ("email.bounced", "email.complained"):
            return HttpResponse(status=200)

        data = payload.get("data", {})
        to_emails = data.get("to", [])
        from_email = data.get("from", "")
        subject = data.get("subject", "")
        email_id = data.get("email_id", "")

        # Only notify for emails sent from our domain
        if "sundkom.dk" not in from_email:
            return HttpResponse(status=200)

        if event_type == "email.bounced":
            event_label = "Bounce"
        else:
            event_label = "Klage (spam)"

        # Mark bounced emails and look up affected persons
        person_rows = ""
        for email in to_emails:
            mark_email_bounced(email)
            owners = lookup_email_owner(email)
            if owners:
                for name, school, role in owners:
                    person_rows += f"<li><strong>{name}</strong> ({role}) — {school}</li>\n"
            else:
                person_rows += f"<li>{email} — <em>ikke fundet i systemet</em></li>\n"

        notification_subject = f"[Basal] Email {event_label}: {', '.join(to_emails)}"
        notification_body = f"""
<p><strong>Email {event_label}</strong></p>

<p><strong>Berørte personer:</strong></p>
<ul>
{person_rows}
</ul>

<p><strong>Email-detaljer:</strong></p>
<ul>
  <li><strong>Modtager:</strong> {", ".join(to_emails)}</li>
  <li><strong>Afsender:</strong> {from_email}</li>
  <li><strong>Emne:</strong> {subject}</li>
  <li><strong>Email ID:</strong> {email_id}</li>
  <li><strong>Hændelse:</strong> {event_type}</li>
</ul>
"""

        if not getattr(settings, "RESEND_API_KEY", None):
            logger.info(f"[WEBHOOK] {event_label} for {to_emails} — no API key, skipping notification")
            return HttpResponse(status=200)

        try:
            resend.api_key = settings.RESEND_API_KEY
            resend.Emails.send(
                {
                    "from": settings.DEFAULT_FROM_EMAIL,
                    "to": [BOUNCE_NOTIFICATION_RECIPIENT],
                    "subject": notification_subject,
                    "html": notification_body,
                }
            )
            logger.info(f"[WEBHOOK] Sent {event_label} notification for {to_emails}")
        except Exception as e:
            logger.error(f"[WEBHOOK] Failed to send {event_label} notification: {e}")

        return HttpResponse(status=200)
