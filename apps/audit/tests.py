from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase

from apps.audit.models import ActionType, ActivityLog
from apps.courses.models import Course, CourseSignUp, Location
from apps.schools.models import School


class AuditDeleteTest(TestCase):
    """Tests for audit logging during model deletion."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.school = School.objects.create(
            name="Test School", adresse="Test Address", kommune="Test Kommune", enrolled_at=date.today()
        )
        self.location = Location.objects.create(name="Test Location")
        self.course = Course.objects.create(
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=7),
            location=self.location,
            capacity=30,
        )

    def test_delete_course_creates_audit_log(self):
        """Deleting a course should create an audit log entry."""
        course_pk = self.course.pk

        self.course.delete()

        # Verify audit log was created
        log = ActivityLog.objects.filter(object_id=course_pk, action=ActionType.DELETE).first()

        self.assertIsNotNone(log)
        self.assertEqual(log.action, ActionType.DELETE)
        self.assertIn("Kompetenceudviklingskursus", log.object_repr)
        # related_course should be None since the course itself was deleted
        self.assertIsNone(log.related_course)

    def test_delete_school_creates_audit_log(self):
        """Deleting a school should create an audit log entry."""
        # Create a school without enrollments to allow hard delete
        school = School.objects.create(name="Delete Test School", adresse="Test Address", kommune="Test Kommune")
        school_pk = school.pk

        # Hard delete (bypass soft delete for test)
        School.objects.filter(pk=school_pk).delete()

        # Verify audit log was created
        log = ActivityLog.objects.filter(object_id=school_pk, action=ActionType.DELETE).first()

        self.assertIsNotNone(log)
        self.assertEqual(log.action, ActionType.DELETE)
        # related_school should be None since the school itself was deleted
        self.assertIsNone(log.related_school)

    def test_delete_course_with_signups(self):
        """Deleting a course should cascade delete signups and create audit logs."""
        signup = CourseSignUp.objects.create(
            course=self.course,
            school=self.school,
            participant_name="Test Participant",
            participant_email="test@example.com",
        )
        signup_pk = signup.pk
        course_pk = self.course.pk

        # Clear existing logs
        ActivityLog.objects.all().delete()

        self.course.delete()

        # Verify signup was deleted
        self.assertFalse(CourseSignUp.objects.filter(pk=signup_pk).exists())

        # Verify audit logs were created for both
        course_log = ActivityLog.objects.filter(object_id=course_pk, action=ActionType.DELETE).first()
        self.assertIsNotNone(course_log)

        signup_log = ActivityLog.objects.filter(object_id=signup_pk, action=ActionType.DELETE).first()
        self.assertIsNotNone(signup_log)
        # DELETE actions don't set related FKs to avoid cascade issues
        self.assertIsNone(signup_log.related_course)
        self.assertIsNone(signup_log.related_school)

    def test_delete_signup_no_fk_references(self):
        """DELETE audit logs don't set FK references to avoid cascade issues."""
        signup = CourseSignUp.objects.create(
            course=self.course,
            school=self.school,
            participant_name="Test Participant",
            participant_email="test@example.com",
        )
        signup_pk = signup.pk

        # Clear existing logs
        ActivityLog.objects.all().delete()

        signup.delete()

        log = ActivityLog.objects.filter(object_id=signup_pk, action=ActionType.DELETE).first()

        self.assertIsNotNone(log)
        # DELETE actions don't set related FKs
        self.assertIsNone(log.related_course)
        self.assertIsNone(log.related_school)
        # But object_repr captures the context
        self.assertIn("Test Participant", log.object_repr)


class AuditCreateUpdateTest(TestCase):
    """Tests for audit logging during model create and update."""

    def test_create_course_creates_audit_log(self):
        """Creating a course should create an audit log entry."""
        course = Course.objects.create(
            start_date=date.today() + timedelta(days=7), end_date=date.today() + timedelta(days=7), capacity=30
        )

        log = ActivityLog.objects.filter(object_id=course.pk, action=ActionType.CREATE).first()

        self.assertIsNotNone(log)
        self.assertEqual(log.action, ActionType.CREATE)
        self.assertEqual(log.related_course, course)

    def test_update_course_creates_audit_log(self):
        """Updating a course should create an audit log entry with changes."""
        course = Course.objects.create(
            start_date=date.today() + timedelta(days=7), end_date=date.today() + timedelta(days=7), capacity=30
        )

        # Clear create log
        ActivityLog.objects.all().delete()

        course.capacity = 50
        course.save()

        log = ActivityLog.objects.filter(object_id=course.pk, action=ActionType.UPDATE).first()

        self.assertIsNotNone(log)
        self.assertEqual(log.action, ActionType.UPDATE)
        self.assertIn("capacity", log.changes)
        self.assertEqual(log.changes["capacity"]["old"], 30)
        self.assertEqual(log.changes["capacity"]["new"], 50)
