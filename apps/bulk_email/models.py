from django.contrib.auth import get_user_model
from django.db import models

from apps.schools.models import Person, School

User = get_user_model()


class BulkEmail(models.Model):
    KOORDINATOR = "koordinator"
    OEKONOMISK_ANSVARLIG = "oekonomisk_ansvarlig"
    BEGGE = "begge"
    FOERSTE_KONTAKT = "foerste_kontakt"
    ALLE_KONTAKTER = "alle_kontakter"
    RECIPIENT_TYPE_CHOICES = [
        (KOORDINATOR, "Koordinator"),
        (OEKONOMISK_ANSVARLIG, "Økonomiansvarlig"),
        (BEGGE, "Koordinator + Økonomiansvarlig"),
        (FOERSTE_KONTAKT, "Første kontakt"),
        (ALLE_KONTAKTER, "Alle kontakter"),
    ]

    name = models.CharField(max_length=255, blank=True, default="")
    subject = models.CharField(max_length=500)
    body_html = models.TextField()
    recipient_type = models.CharField(max_length=30, choices=RECIPIENT_TYPE_CHOICES)
    filter_params = models.JSONField(default=dict)
    sent_at = models.DateTimeField(null=True, blank=True)
    sent_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Masseudsendelse"
        verbose_name_plural = "Masseudsendelser"

    def __str__(self):
        label = self.name or self.subject
        return f"{label} ({self.sent_at or 'ikke sendt'})"

    @property
    def is_sent(self):
        return self.sent_at is not None

    @property
    def is_draft(self):
        """True if not yet sent and no recipients (never started sending)."""
        return self.sent_at is None and not self.recipients.exists()

    @property
    def is_interrupted(self):
        """True if sending started but sent_at was never set."""
        return self.sent_at is None and self.recipients.exists()

    def get_filter_summary_display(self):
        """Return a human-readable summary of stored filter_params."""
        from django.http import QueryDict

        from apps.schools.mixins import get_filter_summary

        qs = QueryDict(mutable=True)
        qs.update(self.filter_params)

        class _FakeRequest:
            GET = qs

        return get_filter_summary(_FakeRequest())


class BulkEmailAttachment(models.Model):
    bulk_email = models.ForeignKey(
        BulkEmail, null=True, blank=True, on_delete=models.SET_NULL, related_name="attachments"
    )
    file = models.FileField(upload_to="bulk_email_attachments/")
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at"]

    def __str__(self):
        return self.filename


class BulkEmailRecipient(models.Model):
    bulk_email = models.ForeignKey(BulkEmail, on_delete=models.CASCADE, related_name="recipients")
    person = models.ForeignKey(Person, null=True, on_delete=models.SET_NULL)
    school = models.ForeignKey(School, null=True, on_delete=models.SET_NULL)
    email = models.CharField(max_length=254)
    success = models.BooleanField(default=False)
    error_message = models.CharField(max_length=500, blank=True)
    bounced_at = models.DateTimeField(null=True, blank=True, verbose_name="Bouncet")
    resend_email_id = models.CharField(max_length=100, blank=True)
    resent_to = models.CharField(max_length=254, blank=True, verbose_name="Gensendt til")
    resent_at = models.DateTimeField(null=True, blank=True, verbose_name="Gensendt")

    class Meta:
        ordering = ["school__name"]

    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.email}"
