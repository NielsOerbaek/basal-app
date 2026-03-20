from django.contrib.auth.models import User
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


class EmailTemplateAdminTest(TestCase):
    def setUp(self):
        self.admin_user, _ = User.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@test.com", "is_staff": True, "is_superuser": True},
        )
        self.admin_user.set_password("password")
        self.admin_user.save()
        self.client.force_login(self.admin_user)
        # Ensure templates exist
        for et in EmailType.values:
            EmailTemplate.objects.get_or_create(
                email_type=et,
                defaults={"subject": "Test", "body_html": "<p>Test</p>", "is_active": True},
            )

    def test_admin_cannot_add_template(self):
        """Add button should not be available — returns 403."""
        response = self.client.get("/admin/emails/emailtemplate/add/")
        self.assertEqual(response.status_code, 403)

    def test_admin_cannot_delete_template(self):
        """Delete action should not be available."""
        template = EmailTemplate.objects.first()
        response = self.client.post(
            f"/admin/emails/emailtemplate/{template.pk}/delete/",
            {"post": "yes"},
        )
        self.assertEqual(response.status_code, 403)

    def test_email_type_is_readonly_on_edit(self):
        """email_type field should be read-only when editing."""
        template = EmailTemplate.objects.first()
        response = self.client.get(f"/admin/emails/emailtemplate/{template.pk}/change/")
        self.assertEqual(response.status_code, 200)
        # email_type should not be an editable field in the form
        self.assertNotContains(response, 'name="email_type"')

    def test_description_is_shown_on_edit(self):
        """description field should be visible when editing."""
        template = EmailTemplate.objects.filter(description__gt="").first()
        if template:
            response = self.client.get(f"/admin/emails/emailtemplate/{template.pk}/change/")
            self.assertContains(response, template.description)
