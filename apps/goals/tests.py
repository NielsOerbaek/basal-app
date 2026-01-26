from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.core.models import ProjectSettings
from apps.courses.models import AttendanceStatus, Course, CourseSignUp, Location
from apps.schools.models import School

from .calculations import (
    get_current_school_year,
    get_metrics_for_year,
    get_school_year,
    get_school_year_dates,
)
from .constants import PROJECT_TARGETS, PROJECT_TOTALS, PROJECT_YEARS


class SchoolYearHelperTests(TestCase):
    """Tests for school year helper functions."""

    def test_get_school_year_august_onwards(self):
        """Dates Aug-Dec return current/next year format."""
        self.assertEqual(get_school_year(date(2024, 8, 1)), "2024/25")
        self.assertEqual(get_school_year(date(2024, 12, 31)), "2024/25")
        self.assertEqual(get_school_year(date(2025, 8, 15)), "2025/26")

    def test_get_school_year_before_august(self):
        """Dates Jan-Jul return previous/current year format."""
        self.assertEqual(get_school_year(date(2025, 1, 1)), "2024/25")
        self.assertEqual(get_school_year(date(2025, 7, 31)), "2024/25")
        self.assertEqual(get_school_year(date(2026, 3, 15)), "2025/26")

    def test_get_school_year_dates(self):
        """Returns correct date range for school year string."""
        start, end = get_school_year_dates("2024/25")
        self.assertEqual(start, date(2024, 8, 1))
        self.assertEqual(end, date(2025, 7, 31))

        start, end = get_school_year_dates("2025/26")
        self.assertEqual(start, date(2025, 8, 1))
        self.assertEqual(end, date(2026, 7, 31))

    def test_get_current_school_year(self):
        """Returns school year for today."""
        today = date.today()
        expected = get_school_year(today)
        self.assertEqual(get_current_school_year(), expected)


class ConstantsTests(TestCase):
    """Tests for project constants."""

    def test_project_years_order(self):
        """PROJECT_YEARS are in chronological order."""
        self.assertEqual(PROJECT_YEARS, ["2024/25", "2025/26", "2026/27", "2027/28", "2028/29"])

    def test_project_targets_all_years_present(self):
        """All project years have targets defined."""
        for year in PROJECT_YEARS:
            self.assertIn(year, PROJECT_TARGETS)

    def test_project_totals_match_sum(self):
        """PROJECT_TOTALS should match sum of yearly targets."""
        for key in ["new_schools", "courses", "trained_total", "trained_teachers"]:
            total = sum(PROJECT_TARGETS[year][key] for year in PROJECT_YEARS)
            self.assertEqual(
                PROJECT_TOTALS[key], total, f"Mismatch for {key}: expected {total}, got {PROJECT_TOTALS[key]}"
            )


class MetricsCalculationTests(TestCase):
    """Tests for metrics calculation functions."""

    def setUp(self):
        # Ensure ProjectSettings exists with defaults
        ProjectSettings.get()
        # Create a shared test location
        self.location = Location.objects.create(name="Test Location")

    def test_new_schools_count(self):
        """Counts schools enrolled in given year."""
        # Create school enrolled in 2024/25
        School.objects.create(
            name="New School",
            adresse="Test Address",
            kommune="Test Kommune",
            enrolled_at=date(2024, 9, 1),  # Sept 2024 = 2024/25
        )
        # Create school enrolled in different year
        School.objects.create(
            name="Old School",
            adresse="Test Address",
            kommune="Test Kommune",
            enrolled_at=date(2023, 9, 1),  # 2023/24
        )

        metrics = get_metrics_for_year("2024/25")
        self.assertEqual(metrics["new_schools"], 1)

    def test_anchoring_schools_count(self):
        """Counts schools from previous years still active."""
        # School enrolled before 2024/25, still active
        School.objects.create(
            name="Anchoring School", adresse="Test Address", kommune="Test Kommune", enrolled_at=date(2023, 9, 1)
        )
        # School enrolled before 2024/25, but opted out
        School.objects.create(
            name="Opted Out School",
            adresse="Test Address",
            kommune="Test Kommune",
            enrolled_at=date(2023, 9, 1),
            opted_out_at=date(2024, 6, 1),  # Opted out before 2024/25
        )

        metrics = get_metrics_for_year("2024/25")
        self.assertEqual(metrics["anchoring"], 1)

    def test_courses_count(self):
        """Counts courses in given school year."""
        # Course in 2024/25
        Course.objects.create(start_date=date(2024, 10, 1), end_date=date(2024, 10, 1), location=self.location)
        # Course in different year
        Course.objects.create(
            start_date=date(2024, 3, 1),  # March 2024 = 2023/24
            end_date=date(2024, 3, 1),
            location=self.location,
        )

        metrics = get_metrics_for_year("2024/25")
        self.assertEqual(metrics["courses"], 1)

    def test_trained_participants_counts_attended_only(self):
        """Only counts participants with attendance=PRESENT."""
        school = School.objects.create(name="Test School", adresse="Test Address", kommune="Test Kommune")
        course = Course.objects.create(start_date=date(2024, 10, 1), end_date=date(2024, 10, 1), location=self.location)
        # Present participant
        CourseSignUp.objects.create(
            school=school, course=course, participant_name="Present Person", attendance=AttendanceStatus.PRESENT
        )
        # Absent participant
        CourseSignUp.objects.create(
            school=school, course=course, participant_name="Absent Person", attendance=AttendanceStatus.ABSENT
        )
        # Unmarked participant
        CourseSignUp.objects.create(
            school=school, course=course, participant_name="Unmarked Person", attendance=AttendanceStatus.UNMARKED
        )

        metrics = get_metrics_for_year("2024/25")
        self.assertEqual(metrics["trained_total"], 1)

    def test_trained_teachers_filters_by_is_underviser(self):
        """Only counts is_underviser=True participants."""
        school = School.objects.create(name="Test School", adresse="Test Address", kommune="Test Kommune")
        course = Course.objects.create(start_date=date(2024, 10, 1), end_date=date(2024, 10, 1), location=self.location)
        # Teacher (is_underviser=True)
        CourseSignUp.objects.create(
            school=school,
            course=course,
            participant_name="Teacher",
            attendance=AttendanceStatus.PRESENT,
            is_underviser=True,
        )
        # Leader (is_underviser=False)
        CourseSignUp.objects.create(
            school=school,
            course=course,
            participant_name="Leader",
            attendance=AttendanceStatus.PRESENT,
            is_underviser=False,
        )

        metrics = get_metrics_for_year("2024/25")
        self.assertEqual(metrics["trained_total"], 2)
        self.assertEqual(metrics["trained_teachers"], 1)

    def test_klasseforloeb_calculation(self):
        """Klasseforløb = trained_teachers * multiplier."""
        settings = ProjectSettings.get()
        settings.klasseforloeb_per_teacher_per_year = Decimal("2.0")
        settings.save()

        school = School.objects.create(name="Test School", adresse="Test Address", kommune="Test Kommune")
        course = Course.objects.create(start_date=date(2024, 10, 1), end_date=date(2024, 10, 1), location=self.location)
        CourseSignUp.objects.create(
            school=school,
            course=course,
            participant_name="Teacher 1",
            attendance=AttendanceStatus.PRESENT,
            is_underviser=True,
        )
        CourseSignUp.objects.create(
            school=school,
            course=course,
            participant_name="Teacher 2",
            attendance=AttendanceStatus.PRESENT,
            is_underviser=True,
        )

        metrics = get_metrics_for_year("2024/25")
        self.assertEqual(metrics["klasseforloeb"], Decimal("4.0"))  # 2 teachers * 2.0

    def test_students_calculation(self):
        """Students = klasseforløb * students_per_klasseforloeb."""
        settings = ProjectSettings.get()
        settings.klasseforloeb_per_teacher_per_year = Decimal("1.0")
        settings.students_per_klasseforloeb = Decimal("20.0")
        settings.save()

        school = School.objects.create(name="Test School", adresse="Test Address", kommune="Test Kommune")
        course = Course.objects.create(start_date=date(2024, 10, 1), end_date=date(2024, 10, 1), location=self.location)
        CourseSignUp.objects.create(
            school=school,
            course=course,
            participant_name="Teacher",
            attendance=AttendanceStatus.PRESENT,
            is_underviser=True,
        )

        metrics = get_metrics_for_year("2024/25")
        self.assertEqual(metrics["klasseforloeb"], Decimal("1.0"))
        self.assertEqual(metrics["students"], Decimal("20.0"))


class ProjectGoalsViewTests(TestCase):
    """Tests for project goals views."""

    def setUp(self):
        from django.contrib.auth.models import User
        from django.test import Client

        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123", is_staff=True)

    def test_project_goals_requires_login(self):
        """Project goals page should redirect unauthenticated users."""
        from django.urls import reverse

        response = self.client.get(reverse("goals:project-goals"))
        self.assertRedirects(response, "/login/?next=/projektmaal/")

    def test_project_goals_page_loads(self):
        """Project goals page should load for staff users."""
        from django.urls import reverse

        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("goals:project-goals"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "goals/project_goals.html")

    def test_project_goals_shows_all_years(self):
        """Project goals page should show all 5 years."""
        from django.urls import reverse

        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("goals:project-goals"))
        self.assertContains(response, "2024/25")
        self.assertContains(response, "2025/26")
        self.assertContains(response, "2026/27")
        self.assertContains(response, "2027/28")
        self.assertContains(response, "2028/29")

    def test_project_settings_update(self):
        """Settings update should modify ProjectSettings."""
        from django.urls import reverse

        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            reverse("goals:settings-update"),
            {
                "klasseforloeb_per_teacher_per_year": "1.5",
                "students_per_klasseforloeb": "20.0",
            },
        )
        self.assertRedirects(response, reverse("goals:project-goals"))

        settings = ProjectSettings.get()
        self.assertEqual(settings.klasseforloeb_per_teacher_per_year, Decimal("1.5"))
        self.assertEqual(settings.students_per_klasseforloeb, Decimal("20.0"))
