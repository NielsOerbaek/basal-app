import logging

import resend
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from svix.webhooks import Webhook, WebhookVerificationError

logger = logging.getLogger(__name__)

BOUNCE_NOTIFICATION_RECIPIENT = "basal@sundkom.dk"


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
