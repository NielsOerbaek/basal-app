from django.test import TestCase, override_settings

from apps.emails.models import EmailTemplate, EmailType
from apps.schools.models import School


class SchoolEnrollmentEmailTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
            signup_password="bafimoku",
            signup_token="abc123token",
        )
        # Ensure the email template exists
        EmailTemplate.objects.get_or_create(
            email_type=EmailType.SCHOOL_ENROLLMENT_CONFIRMATION,
            defaults={
                "subject": "Velkommen til Basal - {{ school_name }}",
                "body_html": "<p>Hej {{ contact_name }},</p><p>Velkommen!</p>",
                "is_active": True,
            },
        )

    @override_settings(RESEND_API_KEY=None)
    def test_send_enrollment_confirmation_returns_true(self):
        """send_school_enrollment_confirmation returns True in dev mode."""
        from apps.emails.services import send_school_enrollment_confirmation

        result = send_school_enrollment_confirmation(
            self.school, contact_email="test@example.com", contact_name="Test Person"
        )
        self.assertTrue(result)

    @override_settings(RESEND_API_KEY=None)
    def test_send_enrollment_confirmation_returns_false_without_template(self):
        """send_school_enrollment_confirmation returns False when template missing."""
        from apps.emails.services import send_school_enrollment_confirmation

        EmailTemplate.objects.filter(email_type=EmailType.SCHOOL_ENROLLMENT_CONFIRMATION).delete()

        result = send_school_enrollment_confirmation(
            self.school, contact_email="test@example.com", contact_name="Test Person"
        )
        self.assertFalse(result)
