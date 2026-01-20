from datetime import date, timedelta

import pytest
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from apps.contacts.models import ContactTime
from apps.courses.models import Course, CourseSignUp
from apps.schools.models import Invoice, Person, School, SchoolComment, SchoolYear


class DashboardViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123", is_staff=True)

    def test_dashboard_requires_login(self):
        """Dashboard should redirect unauthenticated users to login."""
        response = self.client.get(reverse("core:dashboard"))
        self.assertRedirects(response, "/login/?next=/")

    def test_dashboard_loads_for_staff(self):
        """Dashboard should load successfully for staff users."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/dashboard.html")


@pytest.fixture
def smoke_test_data(db, staff_user):
    """Create all necessary objects for smoke testing views."""
    # Create school year (use get_or_create to avoid conflicts)
    today = date.today()
    if today.month >= 8:
        start = date(today.year, 8, 1)
        end = date(today.year + 1, 7, 31)
        name = f"{today.year}-{today.year + 1}"
    else:
        start = date(today.year - 1, 8, 1)
        end = date(today.year, 7, 31)
        name = f"{today.year - 1}-{today.year}"

    school_year, _ = SchoolYear.objects.get_or_create(
        name=name,
        defaults={"start_date": start, "end_date": end},
    )

    # Create school
    school = School.objects.create(
        name="Smoke Test School",
        adresse="Test Address 123",
        kommune="Test Kommune",
        enrolled_at=date.today() - timedelta(days=30),
    )

    # Create person
    person = Person.objects.create(
        school=school,
        name="Test Person",
        email="person@test.com",
        role="koordinator",
    )

    # Create school comment
    comment = SchoolComment.objects.create(
        school=school,
        created_by=staff_user,
        comment="Test comment",
    )

    # Create invoice
    invoice = Invoice.objects.create(
        school=school,
        invoice_number="TEST-001",
        amount=1000,
        date=date.today(),
    )

    # Create course
    course = Course.objects.create(
        title="Smoke Test Course",
        start_date=date.today() + timedelta(days=7),
        end_date=date.today() + timedelta(days=7),
        location="Test Location",
        capacity=30,
        is_published=True,
    )

    # Create course signup
    signup = CourseSignUp.objects.create(
        school=school,
        course=course,
        participant_name="Test Participant",
        participant_email="participant@test.com",
    )

    # Create contact time
    contact = ContactTime.objects.create(
        school=school,
        created_by=staff_user,
        contacted_date=date.today(),
        comment="Test contact",
    )

    return {
        "school_year": school_year,
        "school": school,
        "person": person,
        "comment": comment,
        "invoice": invoice,
        "course": course,
        "signup": signup,
        "contact": contact,
        "user": staff_user,
    }


class ViewSmokeTests:
    """
    Smoke tests to verify all views return valid responses (no 500 errors).

    These tests hit GET endpoints to catch crashes, import errors, and
    basic template rendering issues.
    """

    # URLs that don't require any object IDs
    SIMPLE_URLS = [
        ("core:dashboard", {}),
        ("schools:list", {}),
        ("schools:create", {}),
        ("schools:kommune-list", {}),
        ("schools:export", {}),
        ("schools:autocomplete", {}),
        ("schools:school-year-list", {}),
        ("schools:school-year-create", {}),
        ("schools:missing-invoices", {}),
        ("courses:list", {}),
        ("courses:create", {}),
        ("courses:export", {}),
        ("courses:signup-list", {}),
        ("courses:signup-export", {}),
        ("contacts:list", {}),
        ("contacts:create", {}),
        ("contacts:export", {}),
        ("accounts:user-list", {}),
        ("accounts:user-create", {}),
        ("audit:activity_list", {}),
    ]

    # Public URLs (no auth required)
    PUBLIC_URLS = [
        ("login", {}),
        ("public-signup", {}),
        ("signup-success", {}),
    ]


@pytest.mark.django_db
class TestViewSmokeStaff:
    """Smoke tests for staff-accessible views."""

    def test_simple_urls_no_500(self, staff_client, smoke_test_data):
        """All simple URLs should not return 500 errors for staff."""
        for url_name, kwargs in ViewSmokeTests.SIMPLE_URLS:
            url = reverse(url_name, kwargs=kwargs)
            response = staff_client.get(url)
            assert response.status_code != 500, f"{url_name} returned 500"

    def test_school_detail_urls(self, staff_client, smoke_test_data):
        """School detail URLs should not return 500 errors."""
        school = smoke_test_data["school"]
        urls = [
            ("schools:detail", {"pk": school.pk}),
            ("schools:update", {"pk": school.pk}),
            ("schools:delete", {"pk": school.pk}),
            ("schools:add-seats", {"pk": school.pk}),
            ("schools:person-create", {"school_pk": school.pk}),
            ("schools:comment-create", {"school_pk": school.pk}),
            ("schools:invoice-create", {"school_pk": school.pk}),
        ]
        for url_name, kwargs in urls:
            url = reverse(url_name, kwargs=kwargs)
            response = staff_client.get(url)
            assert response.status_code != 500, f"{url_name} returned 500"

    def test_kommune_detail_url(self, staff_client, smoke_test_data):
        """Kommune detail URL should not return 500 error."""
        school = smoke_test_data["school"]
        url = reverse("schools:kommune-detail", kwargs={"kommune": school.kommune})
        response = staff_client.get(url)
        assert response.status_code != 500

    def test_person_urls(self, staff_client, smoke_test_data):
        """Person URLs should not return 500 errors."""
        person = smoke_test_data["person"]
        urls = [
            ("schools:person-update", {"pk": person.pk}),
            ("schools:person-delete", {"pk": person.pk}),
        ]
        for url_name, kwargs in urls:
            url = reverse(url_name, kwargs=kwargs)
            response = staff_client.get(url)
            assert response.status_code != 500, f"{url_name} returned 500"

    def test_school_year_urls(self, staff_client, smoke_test_data):
        """School year URLs should not return 500 errors."""
        school_year = smoke_test_data["school_year"]
        urls = [
            ("schools:school-year-update", {"pk": school_year.pk}),
            ("schools:school-year-delete", {"pk": school_year.pk}),
        ]
        for url_name, kwargs in urls:
            url = reverse(url_name, kwargs=kwargs)
            response = staff_client.get(url)
            assert response.status_code != 500, f"{url_name} returned 500"

    def test_course_detail_urls(self, staff_client, smoke_test_data):
        """Course detail URLs should not return 500 errors."""
        course = smoke_test_data["course"]
        urls = [
            ("courses:detail", {"pk": course.pk}),
            ("courses:update", {"pk": course.pk}),
            ("courses:delete", {"pk": course.pk}),
            ("courses:rollcall", {"pk": course.pk}),
            ("courses:bulk-import", {"pk": course.pk}),
            ("courses:material-create", {"course_pk": course.pk}),
        ]
        for url_name, kwargs in urls:
            url = reverse(url_name, kwargs=kwargs)
            response = staff_client.get(url)
            assert response.status_code != 500, f"{url_name} returned 500"

    def test_signup_urls(self, staff_client, smoke_test_data):
        """Course signup URLs should not return 500 errors."""
        signup = smoke_test_data["signup"]
        urls = [
            ("courses:signup-delete", {"pk": signup.pk}),
        ]
        for url_name, kwargs in urls:
            url = reverse(url_name, kwargs=kwargs)
            response = staff_client.get(url)
            assert response.status_code != 500, f"{url_name} returned 500"

    def test_contact_detail_urls(self, staff_client, smoke_test_data):
        """Contact detail URLs should not return 500 errors."""
        contact = smoke_test_data["contact"]
        urls = [
            ("contacts:detail", {"pk": contact.pk}),
            ("contacts:update", {"pk": contact.pk}),
            ("contacts:delete", {"pk": contact.pk}),
        ]
        for url_name, kwargs in urls:
            url = reverse(url_name, kwargs=kwargs)
            response = staff_client.get(url)
            assert response.status_code != 500, f"{url_name} returned 500"

    def test_user_detail_urls(self, staff_client, smoke_test_data):
        """User detail URLs should not return 500 errors."""
        user = smoke_test_data["user"]
        urls = [
            ("accounts:user-detail", {"pk": user.pk}),
            ("accounts:user-update", {"pk": user.pk}),
        ]
        for url_name, kwargs in urls:
            url = reverse(url_name, kwargs=kwargs)
            response = staff_client.get(url)
            assert response.status_code != 500, f"{url_name} returned 500"

    def test_audit_detail_urls(self, staff_client, smoke_test_data):
        """Audit detail URLs should not return 500 errors."""
        school = smoke_test_data["school"]
        course = smoke_test_data["course"]
        urls = [
            ("audit:school_activity", {"school_id": school.pk}),
            ("audit:course_activity", {"course_id": course.pk}),
        ]
        for url_name, kwargs in urls:
            url = reverse(url_name, kwargs=kwargs)
            response = staff_client.get(url)
            assert response.status_code != 500, f"{url_name} returned 500"


@pytest.mark.django_db
class TestPublicViewSmoke:
    """Smoke tests for public (no auth required) views."""

    def test_public_urls_no_500(self, client):
        """Public URLs should not return 500 errors."""
        for url_name, kwargs in ViewSmokeTests.PUBLIC_URLS:
            url = reverse(url_name, kwargs=kwargs)
            response = client.get(url)
            assert response.status_code != 500, f"{url_name} returned 500"

    def test_login_page_loads(self, client):
        """Login page should load successfully."""
        response = client.get(reverse("login"))
        assert response.status_code == 200


@pytest.mark.django_db
class TestAuthRedirects:
    """Test that protected views redirect unauthenticated users."""

    def test_protected_urls_redirect_anon(self, client):
        """Protected URLs should redirect anonymous users to login."""
        protected_urls = [
            "core:dashboard",
            "schools:list",
            "courses:list",
            "contacts:list",
            "accounts:user-list",
            "audit:activity_list",
        ]
        for url_name in protected_urls:
            url = reverse(url_name)
            response = client.get(url)
            assert response.status_code in [302, 403], f"{url_name} should redirect or forbid anonymous users"
