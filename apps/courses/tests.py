import os
import tempfile
from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.schools.models import School

from .models import AttendanceStatus, Course, CourseSignUp


class CourseModelTest(TestCase):
    def test_create_course(self):
        """Course model can be created with start_date and end_date."""
        course = Course.objects.create(
            title='Test Course',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
            location='Test Location',
            capacity=30
        )
        self.assertEqual(course.title, 'Test Course')
        self.assertEqual(course.start_date, date.today())
        self.assertEqual(course.end_date, date.today() + timedelta(days=1))

    def test_course_str_single_day(self):
        """Course __str__ shows single date for same start/end."""
        course = Course.objects.create(
            title='Single Day Course',
            start_date=date(2025, 1, 15),
            end_date=date(2025, 1, 15),
            location='Test Location'
        )
        self.assertIn('2025-01-15', str(course))
        self.assertNotIn('til', str(course))

    def test_course_str_multi_day(self):
        """Course __str__ shows date range for different start/end."""
        course = Course.objects.create(
            title='Multi Day Course',
            start_date=date(2025, 1, 15),
            end_date=date(2025, 1, 17),
            location='Test Location'
        )
        self.assertIn('til', str(course))

    def test_signup_count(self):
        """Course.signup_count returns correct count."""
        school = School.objects.create(
            name='Test School',
            adresse='Test Address',
            kommune='Test Kommune'
        )
        course = Course.objects.create(
            title='Test Course',
            start_date=date.today(),
            end_date=date.today(),
            location='Test Location'
        )
        self.assertEqual(course.signup_count, 0)
        CourseSignUp.objects.create(
            course=course,
            school=school,
            participant_name='Test Participant'
        )
        self.assertEqual(course.signup_count, 1)


class CourseSignUpModelTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name='Test School',
            adresse='Test Address',
            kommune='Test Kommune'
        )
        self.course = Course.objects.create(
            title='Test Course',
            start_date=date.today(),
            end_date=date.today(),
            location='Test Location'
        )

    def test_create_signup(self):
        """CourseSignUp can be created."""
        signup = CourseSignUp.objects.create(
            course=self.course,
            school=self.school,
            participant_name='Test Participant'
        )
        self.assertEqual(signup.attendance, AttendanceStatus.UNMARKED)

    def test_unique_constraint(self):
        """Duplicate signups for same course/school/participant are prevented."""
        CourseSignUp.objects.create(
            course=self.course,
            school=self.school,
            participant_name='Test Participant'
        )
        with self.assertRaises(IntegrityError):
            CourseSignUp.objects.create(
                course=self.course,
                school=self.school,
                participant_name='Test Participant'
            )


class CourseViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True
        )
        self.school = School.objects.create(
            name='Test School',
            adresse='Test Address',
            kommune='Test Kommune',
            enrolled_at=date.today()  # School needs to be enrolled to have seats
        )
        self.course = Course.objects.create(
            title='Test Course',
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=7),
            location='Test Location',
            is_published=True
        )

    def test_course_list_loads(self):
        """Course list should load for staff users."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('courses:list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'courses/course_list.html')

    def test_course_detail_loads(self):
        """Course detail should load for staff users."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('courses:detail', kwargs={'pk': self.course.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'courses/course_detail.html')

    def test_course_create_loads(self):
        """Course create form should load for staff users."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('courses:create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'courses/course_form.html')

    def test_rollcall_loads(self):
        """Rollcall view should load for staff users."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('courses:rollcall', kwargs={'pk': self.course.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'courses/rollcall.html')

    def test_public_signup_loads(self):
        """Public signup should load without authentication."""
        response = self.client.get(reverse('public-signup'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'courses/public_signup.html')

    def test_public_signup_submit(self):
        """Public signup form submission should work."""
        response = self.client.post(reverse('public-signup'), {
            'course': self.course.pk,
            'school': self.school.pk,
            'participant_name': 'Test Person',
            'participant_email': 'test@example.com',
        })
        self.assertRedirects(response, reverse('signup-success'))
        self.assertEqual(CourseSignUp.objects.count(), 1)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CourseMaterialsTest(TestCase):
    """Tests for course materials upload functionality."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True
        )
        self.client.login(username='testuser', password='testpass123')

    def tearDown(self):
        # Clean up uploaded files
        for course in Course.objects.all():
            if course.materials:
                try:
                    course.materials.delete(save=False)
                except Exception:
                    pass

    def test_create_course_with_materials(self):
        """Course can be created with materials file upload."""
        pdf_content = b'%PDF-1.4 test content'
        materials_file = SimpleUploadedFile(
            'test_materials.pdf',
            pdf_content,
            content_type='application/pdf'
        )

        response = self.client.post(reverse('courses:create'), {
            'title': 'Course With Materials',
            'start_date': date.today() + timedelta(days=7),
            'end_date': date.today() + timedelta(days=7),
            'location': 'Test Location',
            'capacity': 30,
            'materials': materials_file,
        })

        self.assertRedirects(response, reverse('courses:list'))
        course = Course.objects.get(title='Course With Materials')
        self.assertTrue(course.materials)
        self.assertIn('test_materials', course.materials.name)

    def test_update_course_with_materials(self):
        """Course materials can be added via update."""
        course = Course.objects.create(
            title='Course Without Materials',
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=7),
            location='Test Location',
            capacity=30
        )
        self.assertFalse(course.materials)

        pdf_content = b'%PDF-1.4 updated content'
        materials_file = SimpleUploadedFile(
            'updated_materials.pdf',
            pdf_content,
            content_type='application/pdf'
        )

        response = self.client.post(reverse('courses:update', kwargs={'pk': course.pk}), {
            'title': course.title,
            'start_date': course.start_date,
            'end_date': course.end_date,
            'location': course.location,
            'capacity': course.capacity,
            'materials': materials_file,
        })

        self.assertRedirects(response, reverse('courses:detail', kwargs={'pk': course.pk}))
        course.refresh_from_db()
        self.assertTrue(course.materials)
        self.assertIn('updated_materials', course.materials.name)

    def test_course_detail_shows_materials_link(self):
        """Course detail page shows download link when materials exist."""
        pdf_content = b'%PDF-1.4 test content'
        materials_file = SimpleUploadedFile(
            'detail_test.pdf',
            pdf_content,
            content_type='application/pdf'
        )

        course = Course.objects.create(
            title='Course With Materials',
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=7),
            location='Test Location',
            capacity=30
        )
        course.materials.save('detail_test.pdf', materials_file)

        response = self.client.get(reverse('courses:detail', kwargs={'pk': course.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Download')
        self.assertContains(response, course.materials.url)

    def test_course_detail_no_materials(self):
        """Course detail page shows dash when no materials."""
        course = Course.objects.create(
            title='Course Without Materials',
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=7),
            location='Test Location',
            capacity=30
        )

        response = self.client.get(reverse('courses:detail', kwargs={'pk': course.pk}))
        self.assertEqual(response.status_code, 200)
        # The "Materiale" row should show "-" not "Download"
        self.assertNotContains(response, 'course_materials/')

    def test_form_has_enctype_multipart(self):
        """Course form should have enctype=multipart/form-data for file uploads."""
        response = self.client.get(reverse('courses:create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'enctype="multipart/form-data"')


class CourseFormDateTest(TestCase):
    """Tests for course form date field population."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True
        )
        self.client.login(username='testuser', password='testpass123')
        self.course = Course.objects.create(
            title='Test Course',
            start_date=date(2025, 6, 15),
            end_date=date(2025, 6, 16),
            location='Test Location',
            capacity=30
        )

    def test_edit_form_populates_dates(self):
        """Course edit form should populate date fields with existing values."""
        response = self.client.get(reverse('courses:update', kwargs={'pk': self.course.pk}))
        self.assertEqual(response.status_code, 200)
        # HTML5 date inputs require YYYY-MM-DD format
        self.assertContains(response, 'value="2025-06-15"')
        self.assertContains(response, 'value="2025-06-16"')
