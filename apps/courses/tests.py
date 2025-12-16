from datetime import date, timedelta

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import Client, TestCase
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
            location='Location',
            contact_name='Contact',
            contact_email='test@example.com'
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
            location='Location',
            contact_name='Contact',
            contact_email='test@example.com'
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
            location='Location',
            contact_name='Contact',
            contact_email='test@example.com'
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
        })
        self.assertRedirects(response, reverse('signup-success'))
        self.assertEqual(CourseSignUp.objects.count(), 1)
