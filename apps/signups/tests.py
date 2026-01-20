import tempfile
from datetime import date, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.courses.models import Course, CourseSignUp
from apps.schools.models import School

from .models import (
    FieldType,
    SchoolSignup,
    SignupAttachment,
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

    def test_create_file_field(self):
        """File upload field can be created."""
        field = SignupFormField.objects.create(
            signup_page=self.page,
            field_type=FieldType.FILE_UPLOAD,
            label="Upload CV",
            allowed_extensions="pdf,doc",
            max_file_size_mb=5,
        )
        self.assertIn("pdf", field.allowed_extensions)


class CourseSignupViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
            enrolled_at=date.today(),
        )
        self.course = Course.objects.create(
            title="Test Course",
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=7),
            location="Test Location",
            is_published=True,
        )

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
                "participant_name": "Test Person",
                "participant_email": "test@example.com",
            },
        )
        self.assertRedirects(response, reverse("signup:course-success"))
        self.assertEqual(CourseSignUp.objects.count(), 1)

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


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CourseSignupWithDynamicFieldsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
            enrolled_at=date.today(),
        )
        self.course = Course.objects.create(
            title="Test Course",
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=7),
            location="Test Location",
            is_published=True,
        )
        self.page = SignupPage.objects.get(page_type=SignupPageType.COURSE_SIGNUP)

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
                "participant_name": "Test Person",
                "participant_email": "test@example.com",
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
                "participant_name": "Test Person",
                "participant_email": "test@example.com",
                checkbox.field_name: "on",
            },
        )
        self.assertRedirects(response, reverse("signup:course-success"))

    def test_file_upload_saved(self):
        """Uploaded file should be saved as SignupAttachment."""
        file_field = SignupFormField.objects.create(
            signup_page=self.page,
            field_type=FieldType.FILE_UPLOAD,
            label="Upload document",
            allowed_extensions="pdf",
            is_required=False,
        )

        pdf_content = b"%PDF-1.4 test content"
        test_file = SimpleUploadedFile("test.pdf", pdf_content, content_type="application/pdf")

        response = self.client.post(
            reverse("signup:course"),
            {
                "course": self.course.pk,
                "school": self.school.pk,
                "participant_name": "Test Person",
                "participant_email": "test@example.com",
                file_field.field_name: test_file,
            },
        )
        self.assertRedirects(response, reverse("signup:course-success"))
        self.assertEqual(SignupAttachment.objects.count(), 1)
        attachment = SignupAttachment.objects.first()
        self.assertEqual(attachment.original_filename, "test.pdf")


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

    def test_school_signup_submit_existing_school(self):
        """School signup with existing school should work."""
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
        self.assertEqual(SchoolSignup.objects.count(), 1)
        signup = SchoolSignup.objects.first()
        self.assertEqual(signup.school, self.school)

    def test_school_signup_submit_new_school(self):
        """School signup with new school name should work."""
        response = self.client.post(
            reverse("signup:school"),
            {
                "municipality": "Test Kommune",
                "school_not_listed": "on",
                "new_school_name": "New Test School",
                "contact_name": "Test Contact",
                "contact_email": "contact@school.dk",
            },
        )
        self.assertRedirects(response, reverse("signup:school-success"))
        self.assertEqual(SchoolSignup.objects.count(), 1)
        signup = SchoolSignup.objects.first()
        self.assertIsNone(signup.school)
        self.assertEqual(signup.new_school_name, "New Test School")

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


class URLBackwardCompatibilityTest(TestCase):
    def test_signup_root_redirects_to_course(self):
        """Root /signup/ should redirect to /signup/course/."""
        response = self.client.get("/signup/")
        self.assertRedirects(response, "/signup/course/")
