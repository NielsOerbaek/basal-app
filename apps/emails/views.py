import json
import logging

import resend
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

BOUNCE_NOTIFICATION_RECIPIENT = "basal@sundkom.dk"


@method_decorator(csrf_exempt, name="dispatch")
class ResendWebhookView(View):
    """
    Webhook endpoint for Resend email events.
    Sends a notification email when a bounce or complaint is received.

    Secured via RESEND_WEBHOOK_SECRET in query param (?token=...).
    """

    def post(self, request):
        # Verify webhook secret
        webhook_secret = getattr(settings, "RESEND_WEBHOOK_SECRET", None)
        if not webhook_secret:
            logger.error("RESEND_WEBHOOK_SECRET not configured")
            return JsonResponse({"error": "not configured"}, status=500)

        token = request.GET.get("token", "")
        if token != webhook_secret:
            return JsonResponse({"error": "unauthorized"}, status=401)

        try:
            payload = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "invalid JSON"}, status=400)

        event_type = payload.get("type", "")

        if event_type not in ("email.bounced", "email.complained"):
            # Acknowledge but ignore other events
            return HttpResponse(status=200)

        data = payload.get("data", {})
        to_emails = data.get("to", [])
        from_email = data.get("from", "")
        subject = data.get("subject", "")
        email_id = data.get("email_id", "")

        if event_type == "email.bounced":
            event_label = "Bounce"
        else:
            event_label = "Klage (spam)"

        notification_subject = f"[Basal] Email {event_label}: {', '.join(to_emails)}"
        notification_body = f"""
<p><strong>Email {event_label}</strong></p>
<ul>
  <li><strong>Modtager:</strong> {', '.join(to_emails)}</li>
  <li><strong>Afsender:</strong> {from_email}</li>
  <li><strong>Emne:</strong> {subject}</li>
  <li><strong>Email ID:</strong> {email_id}</li>
  <li><strong>Hændelse:</strong> {event_type}</li>
</ul>
<p>Tjek Resend-dashboardet for flere detaljer.</p>
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
