from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from apps.courses.models import Course, CourseSignUp
from apps.schools.models import School

from .models import (
    FieldType,
    SignupFormField,
    SignupPage,
    SignupPageType,
)


class SignupPageModelTest(TestCase):
    def test_signup_page_created_by_migration(self):
        """SignupPage records should exist from data migration."""
        self.assertTrue(SignupPage.objects.filter(page_type=SignupPageType.COURSE_SIGNUP).exists())
        self.assertTrue(SignupPage.objects.filter(page_type=SignupPageType.SCHOOL_SIGNUP).exists())

    def test_signup_page_str(self):
        """SignupPage __str__ returns page type display."""
        page = SignupPage.objects.get(page_type=SignupPageType.COURSE_SIGNUP)
        self.assertEqual(str(page), "Kursustilmelding")


class SignupFormFieldModelTest(TestCase):
    def setUp(self):
        self.page = SignupPage.objects.get(page_type=SignupPageType.COURSE_SIGNUP)

    def test_create_checkbox_field(self):
        """Checkbox field can be created."""
        field = SignupFormField.objects.create(
            signup_page=self.page,
            field_type=FieldType.CHECKBOX,
            label="Jeg accepterer vilkårene",
            is_required=True,
        )
        self.assertEqual(field.field_name, f"custom_checkbox_{field.pk}")


class CourseSignupViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
            enrolled_at=date.today(),
            signup_password="testpass",
        )
        self.course = Course.objects.create(
            title="Test Course",
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=7),
            location="Test Location",
            is_published=True,
        )
        # Set up session authentication for course signup
        session = self.client.session
        session["course_signup_school_id"] = self.school.pk
        session.save()

    def test_course_signup_loads(self):
        """Course signup page should load."""
        response = self.client.get(reverse("signup:course"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "signups/course_signup.html")

    def test_course_signup_uses_page_content(self):
        """Course signup should use SignupPage content."""
        page = SignupPage.objects.get(page_type=SignupPageType.COURSE_SIGNUP)
        page.title = "Custom Title"
        page.save()

        response = self.client.get(reverse("signup:course"))
        self.assertContains(response, "Custom Title")

    def test_course_signup_submit(self):
        """Course signup form submission should work."""
        response = self.client.post(
            reverse("signup:course"),
            {
                "course": self.course.pk,
                "school": self.school.pk,
                "participant_name_0": "Test Person",
                "participant_email_0": "test@example.com",
            },
        )
        self.assertRedirects(response, reverse("signup:course-success"))
        self.assertEqual(CourseSignUp.objects.count(), 1)

    def test_course_signup_multiple_participants(self):
        """Course signup with multiple participants should create multiple signups."""
        response = self.client.post(
            reverse("signup:course"),
            {
                "course": self.course.pk,
                "school": self.school.pk,
                "participant_name_0": "First Person",
                "participant_email_0": "first@example.com",
                "participant_title_0": "Teacher",
                "participant_name_1": "Second Person",
                "participant_email_1": "second@example.com",
                "participant_title_1": "Assistant",
            },
        )
        self.assertRedirects(response, reverse("signup:course-success"))
        self.assertEqual(CourseSignUp.objects.count(), 2)

        # Verify both participants were created correctly
        signups = CourseSignUp.objects.all().order_by("participant_name")
        self.assertEqual(signups[0].participant_name, "First Person")
        self.assertEqual(signups[0].participant_email, "first@example.com")
        self.assertEqual(signups[1].participant_name, "Second Person")
        self.assertEqual(signups[1].participant_email, "second@example.com")

    def test_course_signup_success_loads(self):
        """Course signup success page should load."""
        response = self.client.get(reverse("signup:course-success"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "signups/course_signup_success.html")

    def test_inactive_page_shows_unavailable(self):
        """Inactive signup page shows unavailable message."""
        page = SignupPage.objects.get(page_type=SignupPageType.COURSE_SIGNUP)
        page.is_active = False
        page.save()

        response = self.client.get(reverse("signup:course"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "signups/page_unavailable.html")


class CourseSignupWithDynamicFieldsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(
            name="Dynamic Fields School",
            adresse="Test Address",
            kommune="Test Kommune",
            enrolled_at=date.today(),
            signup_password="testpass",
        )
        self.course = Course.objects.create(
            title="Test Course",
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=7),
            location="Test Location",
            is_published=True,
        )
        self.page = SignupPage.objects.get(page_type=SignupPageType.COURSE_SIGNUP)
        # Set up session authentication for course signup
        session = self.client.session
        session["course_signup_school_id"] = self.school.pk
        session.save()

    def test_required_checkbox_validation(self):
        """Required checkbox field should be validated."""
        checkbox = SignupFormField.objects.create(
            signup_page=self.page,
            field_type=FieldType.CHECKBOX,
            label="Accept terms",
            is_required=True,
        )

        response = self.client.post(
            reverse("signup:course"),
            {
                "course": self.course.pk,
                "school": self.school.pk,
                "participant_name_0": "Test Person",
                "participant_email_0": "test@example.com",
                # Missing checkbox field
            },
        )
        self.assertEqual(response.status_code, 200)  # Form re-rendered with errors
        self.assertFormError(response.context["form"], checkbox.field_name, "Dette felt er påkrævet.")

    def test_checkbox_accepted_succeeds(self):
        """Form with checked checkbox should succeed."""
        checkbox = SignupFormField.objects.create(
            signup_page=self.page,
            field_type=FieldType.CHECKBOX,
            label="Accept terms",
            is_required=True,
        )

        response = self.client.post(
            reverse("signup:course"),
            {
                "course": self.course.pk,
                "school": self.school.pk,
                "participant_name_0": "Test Person",
                "participant_email_0": "test@example.com",
                checkbox.field_name: "on",
            },
        )
        self.assertRedirects(response, reverse("signup:course-success"))


class SchoolSignupViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
        )

    def test_school_signup_loads(self):
        """School signup page should load."""
        response = self.client.get(reverse("signup:school"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "signups/school_signup.html")

    def test_school_signup_enrolls_existing_school(self):
        """School signup with existing school sets enrolled_at and generates credentials."""
        response = self.client.post(
            reverse("signup:school"),
            {
                "municipality": "Test Kommune",
                "school": self.school.pk,
                "contact_name": "Test Contact",
                "contact_email": "contact@school.dk",
            },
        )
        self.assertRedirects(response, reverse("signup:school-success"))
        self.school.refresh_from_db()
        self.assertIsNotNone(self.school.enrolled_at)
        self.assertEqual(len(self.school.signup_password), 19)
        self.assertEqual(len(self.school.signup_token), 32)

    def test_school_signup_creates_new_school(self):
        """School signup with new school name creates school with credentials."""
        response = self.client.post(
            reverse("signup:school"),
            {
                "municipality": "Test Kommune",  # Must be a valid existing municipality
                "school_not_listed": "on",
                "new_school_name": "Brand New School",
                "new_school_address": "New Address 123",
                "contact_name": "Test Contact",
                "contact_email": "contact@school.dk",
            },
        )
        self.assertRedirects(response, reverse("signup:school-success"))
        new_school = School.objects.get(name="Brand New School")
        self.assertIsNotNone(new_school.enrolled_at)
        self.assertEqual(new_school.kommune, "Test Kommune")
        self.assertEqual(new_school.adresse, "New Address 123")
        self.assertEqual(len(new_school.signup_password), 19)

    def test_school_signup_success_loads(self):
        """School signup success page should load."""
        response = self.client.get(reverse("signup:school-success"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "signups/school_signup_success.html")


class SchoolsByKommuneViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        School.objects.create(name="School A", adresse="Addr", kommune="Aarhus")
        School.objects.create(name="School B", adresse="Addr", kommune="Aarhus")
        School.objects.create(name="School C", adresse="Addr", kommune="Copenhagen")

    def test_returns_schools_for_kommune(self):
        """AJAX endpoint returns schools for given kommune."""
        response = self.client.get(reverse("signup:schools-by-kommune"), {"kommune": "Aarhus"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["schools"]), 2)

    def test_returns_empty_for_unknown_kommune(self):
        """AJAX endpoint returns empty for unknown kommune."""
        response = self.client.get(reverse("signup:schools-by-kommune"), {"kommune": "Unknown"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["schools"]), 0)


class CheckSchoolSeatsViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
            enrolled_at=date.today(),
        )

    def test_check_seats_returns_data(self):
        """Check seats endpoint returns seat availability."""
        response = self.client.get(reverse("signup:check-school-seats"), {"school_id": self.school.pk})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("has_available_seats", data)
        self.assertIn("remaining_seats", data)

    def test_check_seats_missing_id(self):
        """Check seats returns error for missing school_id."""
        response = self.client.get(reverse("signup:check-school-seats"))
        self.assertEqual(response.status_code, 400)


class ValidateSchoolPasswordViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
            enrolled_at=date.today(),
            signup_password="bafimoku",
        )

    def test_valid_password_returns_school_id(self):
        """Valid password returns school info."""
        response = self.client.post(
            reverse("signup:validate-password"),
            data='{"password": "bafimoku"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["valid"])
        self.assertEqual(data["school_id"], self.school.pk)
        self.assertEqual(data["school_name"], "Test School")

    def test_password_is_case_insensitive(self):
        """Password validation is case insensitive."""
        response = self.client.post(
            reverse("signup:validate-password"),
            data='{"password": "BAFIMOKU"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["valid"])

    def test_invalid_password_returns_error(self):
        """Invalid password returns error."""
        response = self.client.post(
            reverse("signup:validate-password"),
            data='{"password": "wrongpass"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["valid"])
        self.assertIn("error", data)

    def test_empty_password_returns_error(self):
        """Empty password returns error."""
        response = self.client.post(
            reverse("signup:validate-password"),
            data='{"password": ""}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["valid"])

    def test_password_sets_session(self):
        """Valid password sets school ID in session."""
        response = self.client.post(
            reverse("signup:validate-password"),
            data='{"password": "bafimoku"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session.get("course_signup_school_id"), self.school.pk)

    def test_opted_out_school_password_rejected(self):
        """Password for opted-out school is rejected."""
        self.school.opted_out_at = date.today()
        self.school.save()

        response = self.client.post(
            reverse("signup:validate-password"),
            data='{"password": "bafimoku"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["valid"])

    def test_unenrolled_school_password_rejected(self):
        """Password for unenrolled school is rejected."""
        self.school.enrolled_at = None
        self.school.save()

        response = self.client.post(
            reverse("signup:validate-password"),
            data='{"password": "bafimoku"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["valid"])


class CourseSignupAuthTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(
            name="Auth Test School",
            adresse="Test Address",
            kommune="Test Kommune",
            enrolled_at=date.today(),
            signup_password="bafimoku",
            signup_token="abc123tokenxyz456",
        )
        self.course = Course.objects.create(
            title="Test Course",
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=7),
            location="Test Location",
            is_published=True,
        )
        self.staff_user = User.objects.create_user(username="authstaffuser", password="staffpass", is_staff=True)

    def test_unauthenticated_shows_password_form(self):
        """Unauthenticated user sees password entry form."""
        response = self.client.get(reverse("signup:course"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="password-section"')

    def test_valid_token_shows_form_with_locked_school(self):
        """Valid token in URL shows form with school pre-selected."""
        response = self.client.get(reverse("signup:course") + "?token=abc123tokenxyz456")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Auth Test School")
        # Check session was set
        self.assertEqual(self.client.session.get("course_signup_school_id"), self.school.pk)

    def test_invalid_token_shows_error(self):
        """Invalid token shows error message."""
        response = self.client.get(reverse("signup:course") + "?token=invalidtoken")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ugyldigt link")

    def test_staff_user_sees_full_form(self):
        """Staff user sees form with school dropdown (not locked)."""
        self.client.login(username="authstaffuser", password="staffpass")
        response = self.client.get(reverse("signup:course"))
        self.assertEqual(response.status_code, 200)
        # Should NOT have password section
        self.assertNotContains(response, 'id="password-section"')

    def test_session_auth_shows_locked_form(self):
        """User with session auth sees form with locked school."""
        session = self.client.session
        session["course_signup_school_id"] = self.school.pk
        session.save()

        response = self.client.get(reverse("signup:course"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Auth Test School")


class URLBackwardCompatibilityTest(TestCase):
    def test_signup_root_redirects_to_course(self):
        """Root /signup/ should redirect to /signup/course/."""
        response = self.client.get("/signup/")
        self.assertRedirects(response, "/signup/course/")
