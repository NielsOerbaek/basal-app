from django.contrib.auth.models import User
from django.test import TestCase, override_settings

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

    @override_settings(RESEND_API_KEY=None)
    def test_send_enrollment_confirmation_returns_true(self):
        """send_school_enrollment_confirmation returns True in dev mode."""
        from apps.emails.services import send_school_enrollment_confirmation

        result = send_school_enrollment_confirmation(
            self.school, contact_email="test@example.com", contact_name="Test Person"
        )
        self.assertTrue(result)


class SchoolSignupNotificationTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
        )
        # Create user with notification enabled
        self.user = User.objects.create_user(username="notifyuser", email="notify@example.com", password="testpass")
        self.user.profile.notify_on_school_signup = True
        self.user.profile.save()

    @override_settings(RESEND_API_KEY=None)
    def test_send_notification_to_subscribed_users(self):
        """send_school_signup_notifications sends to subscribed users."""
        from apps.emails.services import send_school_signup_notifications

        result = send_school_signup_notifications(
            self.school, contact_name="Test Contact", contact_email="contact@school.dk"
        )
        self.assertEqual(result, 1)  # One user notified

    @override_settings(RESEND_API_KEY=None)
    def test_no_notification_when_no_subscribers(self):
        """send_school_signup_notifications returns 0 when no subscribers."""
        self.user.profile.notify_on_school_signup = False
        self.user.profile.save()

        from apps.emails.services import send_school_signup_notifications

        result = send_school_signup_notifications(
            self.school, contact_name="Test Contact", contact_email="contact@school.dk"
        )
        self.assertEqual(result, 0)
