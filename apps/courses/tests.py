import tempfile
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.schools.models import School

from .models import AttendanceStatus, Course, CourseMaterial, CourseSignUp


class CourseModelTest(TestCase):
    def test_create_course(self):
        """Course model can be created with start_date and end_date."""
        course = Course.objects.create(
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
            capacity=30,
        )
        self.assertEqual(course.start_date, date.today())
        self.assertEqual(course.end_date, date.today() + timedelta(days=1))

    def test_course_str_single_day(self):
        """Course __str__ shows single date for same start/end via display_name."""
        course = Course.objects.create(
            start_date=date(2025, 1, 15),
            end_date=date(2025, 1, 15),
        )
        self.assertIn("jan", str(course).lower())
        self.assertNotIn(" - ", str(course))

    def test_course_str_multi_day(self):
        """Course __str__ shows date range for different start/end."""
        course = Course.objects.create(
            start_date=date(2025, 1, 15),
            end_date=date(2025, 1, 17),
        )
        self.assertIn(" - ", str(course))

    def test_display_name_uses_danish_months(self):
        """Course display_name uses Danish month abbreviations."""
        # Test various months to ensure Danish locale is used
        test_cases = [
            (date(2025, 1, 15), "jan"),
            (date(2025, 3, 15), "mar"),
            (date(2025, 5, 15), "maj"),  # Different from English "may"
            (date(2025, 10, 15), "okt"),  # Different from English "oct"
        ]
        for test_date, expected_month in test_cases:
            course = Course.objects.create(start_date=test_date, end_date=test_date)
            self.assertIn(expected_month, course.display_name.lower(), f"Expected {expected_month} for {test_date}")
            course.delete()

    def test_signup_count(self):
        """Course.signup_count returns correct count."""
        school = School.objects.create(name="Test School", adresse="Test Address", kommune="Test Kommune")
        course = Course.objects.create(
            start_date=date.today(),
            end_date=date.today(),
        )
        self.assertEqual(course.signup_count, 0)
        CourseSignUp.objects.create(course=course, school=school, participant_name="Test Participant")
        self.assertEqual(course.signup_count, 1)


class CourseSignUpModelTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="Test School", adresse="Test Address", kommune="Test Kommune")
        self.course = Course.objects.create(
            start_date=date.today(),
            end_date=date.today(),
        )

    def test_create_signup(self):
        """CourseSignUp can be created."""
        signup = CourseSignUp.objects.create(
            course=self.course, school=self.school, participant_name="Test Participant"
        )
        self.assertEqual(signup.attendance, AttendanceStatus.UNMARKED)

    def test_create_signup_with_other_organization(self):
        """CourseSignUp can be created with other_organization instead of school."""
        signup = CourseSignUp.objects.create(
            course=self.course, school=None, other_organization="Frederikshavn Kommune", participant_name="Test Person"
        )
        self.assertEqual(signup.organization_name, "Frederikshavn Kommune")


class CourseViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123", is_staff=True)
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
            enrolled_at=date.today(),  # School needs to be enrolled to have seats
        )
        self.course = Course.objects.create(
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=7),
            is_published=True,
        )

    def test_course_list_loads(self):
        """Course list should load for staff users."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("courses:list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/course_list.html")

    def test_course_detail_loads(self):
        """Course detail should load for staff users."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("courses:detail", kwargs={"pk": self.course.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/course_detail.html")

    def test_course_create_loads(self):
        """Course create form should load for staff users."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("courses:create"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/course_form.html")

    def test_rollcall_loads(self):
        """Rollcall view should load for staff users."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("courses:rollcall", kwargs={"pk": self.course.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/rollcall.html")

    def test_public_signup_loads(self):
        """Public signup should load without authentication."""
        response = self.client.get(reverse("signup:course"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "signups/course_signup.html")

    def test_public_signup_submit(self):
        """Public signup form submission should work when authenticated via session."""
        # Set up session authentication for course signup
        session = self.client.session
        session["course_signup_school_id"] = self.school.pk
        session.save()

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


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CourseMaterialsTest(TestCase):
    """Tests for course materials upload functionality using CourseMaterial model."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123", is_staff=True)
        self.client.login(username="testuser", password="testpass123")
        self.course = Course.objects.create(
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=7),
            capacity=30,
        )

    def tearDown(self):
        # Clean up uploaded files
        for material in CourseMaterial.objects.all():
            if material.file:
                try:
                    material.file.delete(save=False)
                except Exception:
                    pass

    def test_add_material_to_course(self):
        """CourseMaterial can be added to a course via material-create endpoint."""
        pdf_content = b"%PDF-1.4 test content"
        materials_file = SimpleUploadedFile("test_materials.pdf", pdf_content, content_type="application/pdf")

        response = self.client.post(
            reverse("courses:material-create", kwargs={"course_pk": self.course.pk}),
            {"file": materials_file, "name": "Test Material"},
        )

        self.assertRedirects(response, reverse("courses:detail", kwargs={"pk": self.course.pk}))
        self.assertEqual(self.course.course_materials.count(), 1)
        material = self.course.course_materials.first()
        self.assertIn("test_materials", material.file.name)
        self.assertEqual(material.name, "Test Material")

    def test_add_material_without_name(self):
        """CourseMaterial can be added without optional name field."""
        pdf_content = b"%PDF-1.4 test content"
        materials_file = SimpleUploadedFile("unnamed_material.pdf", pdf_content, content_type="application/pdf")

        response = self.client.post(
            reverse("courses:material-create", kwargs={"course_pk": self.course.pk}), {"file": materials_file}
        )

        self.assertRedirects(response, reverse("courses:detail", kwargs={"pk": self.course.pk}))
        self.assertEqual(self.course.course_materials.count(), 1)

    def test_course_detail_shows_materials(self):
        """Course detail page shows materials when they exist."""
        pdf_content = b"%PDF-1.4 test content"
        materials_file = SimpleUploadedFile("detail_test.pdf", pdf_content, content_type="application/pdf")

        material = CourseMaterial.objects.create(course=self.course, name="Test Material")
        material.file.save("detail_test.pdf", materials_file)

        response = self.client.get(reverse("courses:detail", kwargs={"pk": self.course.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Material")
        self.assertContains(response, material.file.url)

    def test_course_detail_no_materials(self):
        """Course detail page shows empty state when no materials."""
        response = self.client.get(reverse("courses:detail", kwargs={"pk": self.course.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ingen kursusmaterialer")

    def test_material_form_has_enctype_multipart(self):
        """Material form should have enctype=multipart/form-data for file uploads."""
        response = self.client.get(reverse("courses:material-create", kwargs={"course_pk": self.course.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'enctype="multipart/form-data"')


class CourseSignUpIsUnderTest(TestCase):
    """Tests for CourseSignUp.is_underviser field."""

    def setUp(self):
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
        )
        self.course = Course.objects.create(
            start_date=date.today(),
            end_date=date.today(),
        )

    def test_is_underviser_default_true(self):
        """CourseSignUp.is_underviser defaults to True."""
        signup = CourseSignUp.objects.create(
            school=self.school,
            course=self.course,
            participant_name="Test Person",
        )
        self.assertTrue(signup.is_underviser)

    def test_is_underviser_can_be_false(self):
        """CourseSignUp.is_underviser can be set to False."""
        signup = CourseSignUp.objects.create(
            school=self.school,
            course=self.course,
            participant_name="Test Leader",
            is_underviser=False,
        )
        self.assertFalse(signup.is_underviser)


class CourseSignUpFormTest(TestCase):
    """Tests for CourseSignUp form."""

    def test_form_includes_is_underviser_field(self):
        """CourseSignUp form includes is_underviser field."""
        from apps.courses.forms import CourseSignUpForm

        form = CourseSignUpForm()
        self.assertIn("is_underviser", form.fields)


class CourseFormDateTest(TestCase):
    """Tests for course form date field population."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123", is_staff=True)
        self.client.login(username="testuser", password="testpass123")
        self.course = Course.objects.create(
            start_date=date(2025, 6, 15),
            end_date=date(2025, 6, 16),
            capacity=30,
        )

    def test_edit_form_populates_dates(self):
        """Course edit form should populate date fields with existing values."""
        response = self.client.get(reverse("courses:update", kwargs={"pk": self.course.pk}))
        self.assertEqual(response.status_code, 200)
        # HTML5 date inputs require YYYY-MM-DD format
        self.assertContains(response, 'value="2025-06-15"')
        self.assertContains(response, 'value="2025-06-16"')


class CourseSignUpParticipantFormTest(TestCase):
    """Tests for CourseSignUpParticipantForm."""

    def test_form_only_has_participant_fields(self):
        """Form should only allow editing participant details, not course."""
        from apps.courses.forms import CourseSignUpParticipantForm

        form = CourseSignUpParticipantForm()
        expected_fields = {"participant_name", "participant_title", "participant_email", "participant_phone"}
        self.assertEqual(set(form.fields.keys()), expected_fields)

    def test_form_saves_participant_details(self):
        """Form should update participant details on existing signup."""
        from apps.courses.forms import CourseSignUpParticipantForm

        course = Course.objects.create(
            start_date=date.today(),
            end_date=date.today(),
        )
        signup = CourseSignUp.objects.create(
            course=course,
            participant_name="Original Name",
            participant_email="original@example.com",
        )
        form = CourseSignUpParticipantForm(
            instance=signup,
            data={
                "participant_name": "Updated Name",
                "participant_title": "Lærer",
                "participant_email": "updated@example.com",
                "participant_phone": "12345678",
            },
        )
        self.assertTrue(form.is_valid())
        updated = form.save()
        self.assertEqual(updated.participant_name, "Updated Name")
        self.assertEqual(updated.participant_email, "updated@example.com")


class InstructorModelTest(TestCase):
    def test_create_instructor(self):
        """Instructor model can be created with a name."""
        from apps.courses.models import Instructor

        instructor = Instructor.objects.create(name="Anders Andersen")
        self.assertEqual(instructor.name, "Anders Andersen")
        self.assertEqual(str(instructor), "Anders Andersen")

    def test_instructor_name_unique(self):
        """Instructor names must be unique."""
        from apps.courses.models import Instructor

        Instructor.objects.create(name="Anders Andersen")
        with self.assertRaises(IntegrityError):
            Instructor.objects.create(name="Anders Andersen")


class LocationModelTest(TestCase):
    def test_create_location(self):
        """Location model can be created with address details."""
        from apps.courses.models import Location

        location = Location.objects.create(
            name="Basal Hovedkontor", street_address="Vesterbrogade 123", postal_code="1620", municipality="København V"
        )
        self.assertEqual(location.name, "Basal Hovedkontor")
        self.assertEqual(str(location), "Basal Hovedkontor")

    def test_location_full_address(self):
        """Location.full_address returns formatted address."""
        from apps.courses.models import Location

        location = Location.objects.create(
            name="Basal Hovedkontor", street_address="Vesterbrogade 123", postal_code="1620", municipality="København V"
        )
        self.assertEqual(location.full_address, "Basal Hovedkontor, Vesterbrogade 123, 1620 København V")

    def test_location_full_address_minimal(self):
        """Location.full_address works with only name."""
        from apps.courses.models import Location

        location = Location.objects.create(name="Online")
        self.assertEqual(location.full_address, "Online")

    def test_location_address_fields_optional(self):
        """Location can be created with only name."""
        from apps.courses.models import Location

        location = Location.objects.create(name="Online")
        self.assertEqual(location.street_address, "")
        self.assertEqual(location.postal_code, "")
        self.assertEqual(location.municipality, "")
