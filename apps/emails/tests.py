from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from apps.courses.models import Course, CourseSignUp, Instructor, Location
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


class SignupContextTest(TestCase):
    def setUp(self):
        self.location = Location.objects.create(
            name="Teststed", street_address="Testvej 1", postal_code="1234", municipality="Testby"
        )
        self.instructor = Instructor.objects.create(name="Hans Hansen")
        self.course = Course.objects.create(
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 2),
            location=self.location,
            capacity=30,
            registration_deadline=date(2026, 5, 15),
        )
        self.course.instructors.add(self.instructor)
        self.school = School.objects.create(name="Test School", adresse="Skolevej 1", kommune="Testby")
        self.signup = CourseSignUp.objects.create(
            course=self.course,
            school=self.school,
            participant_name="Test Deltager",
            participant_email="test@example.com",
            participant_title="Lærer",
        )

    def test_get_signup_context_includes_new_variables(self):
        from apps.emails.services import get_signup_context

        ctx = get_signup_context(self.signup)
        self.assertIn("registration_deadline", ctx)
        self.assertIn("course_end_date", ctx)
        self.assertIn("instructors", ctx)
        self.assertIn("spots_remaining", ctx)
        self.assertEqual(ctx["instructors"], "Hans Hansen")
        self.assertEqual(ctx["spots_remaining"], 29)  # 30 capacity - 1 signup

    def test_get_signup_context_handles_no_deadline(self):
        from apps.emails.services import get_signup_context

        self.course.registration_deadline = None
        self.course.save()
        ctx = get_signup_context(self.signup)
        self.assertEqual(ctx["registration_deadline"], "")


class SchoolEnrollmentContextTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Test School",
            adresse="Skolevej 1",
            postnummer="1234",
            by="Testby",
            kommune="Testkommune",
            ean_nummer="1234567890123",
            signup_token="abc123",
            signup_password="testpass",
        )

    def test_get_school_enrollment_context_includes_new_variables(self):
        from apps.emails.services import get_school_enrollment_context

        ctx = get_school_enrollment_context(self.school, "Test Person")
        self.assertEqual(ctx["school_address"], "Skolevej 1")
        self.assertEqual(ctx["school_municipality"], "Testkommune")
        self.assertEqual(ctx["ean_nummer"], "1234567890123")


class CoordinatorEmailTest(TestCase):
    def setUp(self):
        from apps.schools.models import Person

        self.location = Location.objects.create(
            name="Teststed", street_address="Testvej 1", postal_code="1234", municipality="Testby"
        )
        self.course = Course.objects.create(
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 2),
            location=self.location,
            capacity=30,
        )
        self.school = School.objects.create(name="Test School", adresse="Skolevej 1", kommune="Testby")
        self.coordinator = Person.objects.create(
            school=self.school,
            name="Koordinator Person",
            email="koordinator@example.com",
            is_koordinator=True,
        )
        self.signups = [
            CourseSignUp.objects.create(
                course=self.course,
                school=self.school,
                participant_name="Deltager 1",
                participant_email="d1@example.com",
            ),
            CourseSignUp.objects.create(
                course=self.course,
                school=self.school,
                participant_name="Deltager 2",
                participant_email="d2@example.com",
            ),
        ]
        # Ensure template exists
        EmailTemplate.objects.get_or_create(
            email_type="coordinator_signup",
            defaults={
                "subject": "Tilmelding – {{ school_name }}",
                "body_html": "<p>{{ coordinator_name }}</p>{{ participants_list }}",
                "is_active": True,
            },
        )

    @override_settings(RESEND_API_KEY=None)
    def test_sends_to_coordinator(self):
        from apps.emails.models import EmailLog
        from apps.emails.services import send_coordinator_signup_confirmation

        result = send_coordinator_signup_confirmation(self.school, self.course, self.signups)
        self.assertTrue(result)
        log = EmailLog.objects.filter(email_type="coordinator_signup").first()
        self.assertIsNotNone(log)
        self.assertEqual(log.recipient_email, "koordinator@example.com")
        self.assertEqual(log.recipient_name, "Koordinator Person")

    @override_settings(RESEND_API_KEY=None)
    def test_override_email_replaces_coordinator(self):
        from apps.emails.models import EmailLog
        from apps.emails.services import send_coordinator_signup_confirmation

        result = send_coordinator_signup_confirmation(
            self.school, self.course, self.signups, override_email="other@example.com"
        )
        self.assertTrue(result)
        log = EmailLog.objects.filter(email_type="coordinator_signup").first()
        self.assertEqual(log.recipient_email, "other@example.com")
        # recipient_name should still be the coordinator's name
        self.assertEqual(log.recipient_name, "Koordinator Person")

    @override_settings(RESEND_API_KEY=None)
    def test_skips_when_no_coordinator_and_no_override(self):
        from apps.emails.services import send_coordinator_signup_confirmation

        self.coordinator.delete()
        result = send_coordinator_signup_confirmation(self.school, self.course, self.signups)
        self.assertFalse(result)

    @override_settings(RESEND_API_KEY=None)
    def test_skips_when_coordinator_has_no_email(self):
        from apps.emails.services import send_coordinator_signup_confirmation

        self.coordinator.email = ""
        self.coordinator.save()
        result = send_coordinator_signup_confirmation(self.school, self.course, self.signups)
        self.assertFalse(result)

    @override_settings(RESEND_API_KEY=None)
    def test_context_includes_participants_list(self):
        from apps.emails.services import get_coordinator_signup_context

        ctx = get_coordinator_signup_context(self.coordinator, self.course, self.signups)
        self.assertIn("Deltager 1", ctx["participants_list"])
        self.assertIn("Deltager 2", ctx["participants_list"])
        self.assertEqual(ctx["coordinator_name"], "Koordinator Person")
        self.assertEqual(ctx["school_name"], "Test School")
