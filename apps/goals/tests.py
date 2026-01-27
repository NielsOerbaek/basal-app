from datetime import date
from decimal import Decimal

from django.test import Client, TestCase

from apps.core.models import ProjectSettings
from apps.courses.models import AttendanceStatus, Course, CourseSignUp, Location
from apps.schools.models import School
from apps.schools.school_years import (
    calculate_school_year_for_date,
    get_school_year_dates,
)

from .calculations import (
    get_current_school_year,
    get_metrics_for_year,
)
from .constants import PROJECT_TARGETS, PROJECT_TOTALS, PROJECT_YEARS


class SchoolYearHelperTests(TestCase):
    """Tests for school year helper functions."""

    def test_get_school_year_august_onwards(self):
        """Dates Aug-Dec return current/next year format."""
        self.assertEqual(calculate_school_year_for_date(date(2024, 8, 1)), "2024/25")
        self.assertEqual(calculate_school_year_for_date(date(2024, 12, 31)), "2024/25")
        self.assertEqual(calculate_school_year_for_date(date(2025, 8, 15)), "2025/26")

    def test_get_school_year_before_august(self):
        """Dates Jan-Jul return previous/current year format."""
        self.assertEqual(calculate_school_year_for_date(date(2025, 1, 1)), "2024/25")
        self.assertEqual(calculate_school_year_for_date(date(2025, 7, 31)), "2024/25")
        self.assertEqual(calculate_school_year_for_date(date(2026, 3, 15)), "2025/26")

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
        expected = calculate_school_year_for_date(today)
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


class GoalsDrillDownIntegrationTests(TestCase):
    """
    Integration tests verifying that the project goals metrics match
    the schools shown in the drill-down views.

    These tests ensure consistency between:
    - The counts shown on the goals overview page
    - The schools returned when following drill-down links
    """

    def setUp(self):
        from django.contrib.auth.models import User
        from django.urls import reverse

        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123", is_staff=True)
        self.client.login(username="testuser", password="testpass123")
        self.schools_url = reverse("schools:list")

    def test_new_schools_drilldown_2024_25(self):
        """
        Schools enrolled during 2024/25 (Aug 1 2024 - Jul 31 2025) should appear
        in the 'new' drill-down for that year.
        """
        # Create schools enrolled at different times in 2024/25
        School.objects.create(
            name="Sept 2024 School",
            adresse="Address",
            kommune="Kommune A",
            enrolled_at=date(2024, 9, 15),  # Mid-September 2024
        )
        School.objects.create(
            name="Jan 2025 School",
            adresse="Address",
            kommune="Kommune B",
            enrolled_at=date(2025, 1, 10),  # January 2025 (still 2024/25 school year)
        )
        School.objects.create(
            name="Jul 2025 School",
            adresse="Address",
            kommune="Kommune C",
            enrolled_at=date(2025, 7, 31),  # Last day of 2024/25
        )

        # Schools NOT in 2024/25
        School.objects.create(
            name="Pre-2024/25 School",
            adresse="Address",
            kommune="Kommune D",
            enrolled_at=date(2024, 7, 31),  # Last day of 2023/24
        )
        School.objects.create(
            name="Post-2024/25 School",
            adresse="Address",
            kommune="Kommune E",
            enrolled_at=date(2025, 8, 1),  # First day of 2025/26
        )

        # Get metrics from goals calculation
        metrics = get_metrics_for_year("2024/25")
        self.assertEqual(metrics["new_schools"], 3)

        # Follow the drill-down link
        response = self.client.get(f"{self.schools_url}?status=new&school_year=2024-25")
        self.assertEqual(response.status_code, 200)

        # The response context should contain exactly the 3 new schools
        schools_in_response = list(response.context["object_list"])
        school_names = {s.name for s in schools_in_response}
        self.assertEqual(
            school_names,
            {"Sept 2024 School", "Jan 2025 School", "Jul 2025 School"},
        )

    def test_anchoring_schools_drilldown_2025_26(self):
        """
        Schools enrolled BEFORE 2025/26 (before Aug 1 2025) and still active
        should appear in the 'anchoring' drill-down for 2025/26.
        """
        # Schools that should be anchoring in 2025/26
        School.objects.create(
            name="Early Anchor School",
            adresse="Address",
            kommune="Kommune A",
            enrolled_at=date(2023, 9, 1),  # Enrolled in 2023/24
        )
        School.objects.create(
            name="Late 2024 Anchor School",
            adresse="Address",
            kommune="Kommune B",
            enrolled_at=date(2025, 7, 31),  # Last day of 2024/25 - anchoring in 2025/26
        )

        # Schools NOT anchoring in 2025/26
        School.objects.create(
            name="New in 2025/26 School",
            adresse="Address",
            kommune="Kommune C",
            enrolled_at=date(2025, 8, 1),  # First day of 2025/26 - this is NEW, not anchoring
        )
        School.objects.create(
            name="Opted Out School",
            adresse="Address",
            kommune="Kommune D",
            enrolled_at=date(2024, 9, 1),
            opted_out_at=date(2025, 6, 1),  # Opted out before 2025/26
        )

        # Get metrics from goals calculation
        metrics = get_metrics_for_year("2025/26")
        self.assertEqual(metrics["anchoring"], 2)

        # Follow the drill-down link
        response = self.client.get(f"{self.schools_url}?status=anchoring&school_year=2025-26")
        self.assertEqual(response.status_code, 200)

        schools_in_response = list(response.context["object_list"])
        school_names = {s.name for s in schools_in_response}
        self.assertEqual(
            school_names,
            {"Early Anchor School", "Late 2024 Anchor School"},
        )

    def test_august_boundary_new_vs_anchoring(self):
        """
        Test the August 1st boundary precisely:
        - Enrolled Jul 31 = anchoring next year
        - Enrolled Aug 1 = new in that year
        """
        # School enrolled on Jul 31, 2025 - last day of 2024/25
        School.objects.create(
            name="Jul 31 School",
            adresse="Address",
            kommune="Kommune A",
            enrolled_at=date(2025, 7, 31),
        )
        # School enrolled on Aug 1, 2025 - first day of 2025/26
        School.objects.create(
            name="Aug 1 School",
            adresse="Address",
            kommune="Kommune B",
            enrolled_at=date(2025, 8, 1),
        )

        # For 2025/26:
        # - Jul 31 school should be ANCHORING (enrolled before 2025/26)
        # - Aug 1 school should be NEW (enrolled during 2025/26)
        metrics_2025_26 = get_metrics_for_year("2025/26")
        self.assertEqual(metrics_2025_26["new_schools"], 1)
        self.assertEqual(metrics_2025_26["anchoring"], 1)

        # Verify drill-down for new schools in 2025/26
        response_new = self.client.get(f"{self.schools_url}?status=new&school_year=2025-26")
        new_schools = list(response_new.context["object_list"])
        self.assertEqual(len(new_schools), 1)
        self.assertEqual(new_schools[0].name, "Aug 1 School")

        # Verify drill-down for anchoring schools in 2025/26
        response_anchoring = self.client.get(f"{self.schools_url}?status=anchoring&school_year=2025-26")
        anchoring_schools = list(response_anchoring.context["object_list"])
        self.assertEqual(len(anchoring_schools), 1)
        self.assertEqual(anchoring_schools[0].name, "Jul 31 School")

    def test_drilldown_url_format_variations(self):
        """
        The drill-down should work with different URL year formats.
        """
        School.objects.create(
            name="Test School",
            adresse="Address",
            kommune="Kommune",
            enrolled_at=date(2024, 10, 1),
        )

        # All these URL formats should return the same school
        url_formats = [
            f"{self.schools_url}?status=new&school_year=2024-25",
            f"{self.schools_url}?status=new&school_year=2024-2025",
        ]

        for url in url_formats:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"Failed for URL: {url}")
            schools = list(response.context["object_list"])
            self.assertEqual(len(schools), 1, f"Wrong count for URL: {url}")
            self.assertEqual(schools[0].name, "Test School", f"Wrong school for URL: {url}")

    def test_opted_out_school_not_in_anchoring(self):
        """
        Schools that opted out before a school year starts should not
        appear in the anchoring count for that year.
        """
        # School enrolled in 2023/24, opted out in June 2025 (before 2025/26)
        School.objects.create(
            name="Opted Out Early",
            adresse="Address",
            kommune="Kommune A",
            enrolled_at=date(2023, 10, 1),
            opted_out_at=date(2025, 6, 15),  # Opted out before 2025/26 starts
        )
        # School enrolled in 2023/24, still active
        School.objects.create(
            name="Still Active",
            adresse="Address",
            kommune="Kommune B",
            enrolled_at=date(2023, 10, 1),
        )

        metrics = get_metrics_for_year("2025/26")
        self.assertEqual(metrics["anchoring"], 1)

        response = self.client.get(f"{self.schools_url}?status=anchoring&school_year=2025-26")
        schools = list(response.context["object_list"])
        self.assertEqual(len(schools), 1)
        self.assertEqual(schools[0].name, "Still Active")
