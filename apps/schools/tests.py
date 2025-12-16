from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .models import School


class SchoolModelTest(TestCase):
    def test_create_school(self):
        """School model can be created and saved."""
        school = School.objects.create(
            name='Test School',
            location='Test Location',
            contact_name='Test Contact',
            contact_email='test@example.com'
        )
        self.assertEqual(school.name, 'Test School')
        self.assertTrue(school.is_active)

    def test_soft_delete(self):
        """School soft delete sets is_active to False."""
        school = School.objects.create(
            name='Test School',
            location='Test Location',
            contact_name='Test Contact',
            contact_email='test@example.com'
        )
        school.delete()
        school.refresh_from_db()
        self.assertFalse(school.is_active)

    def test_active_manager(self):
        """School.objects.active() returns only active schools."""
        active = School.objects.create(
            name='Active School',
            location='Location',
            contact_name='Contact',
            contact_email='active@example.com'
        )
        inactive = School.objects.create(
            name='Inactive School',
            location='Location',
            contact_name='Contact',
            contact_email='inactive@example.com',
            is_active=False
        )
        self.assertIn(active, School.objects.active())
        self.assertNotIn(inactive, School.objects.active())


class SchoolViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True
        )
        self.school = School.objects.create(
            name='Test School',
            location='Test Location',
            contact_name='Test Contact',
            contact_email='test@example.com'
        )

    def test_school_list_requires_login(self):
        """School list should redirect unauthenticated users."""
        response = self.client.get(reverse('schools:list'))
        self.assertEqual(response.status_code, 302)

    def test_school_list_loads(self):
        """School list should load for staff users."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('schools:list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'schools/school_list.html')

    def test_school_detail_loads(self):
        """School detail should load for staff users."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('schools:detail', kwargs={'pk': self.school.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'schools/school_detail.html')

    def test_school_create_loads(self):
        """School create form should load for staff users."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('schools:create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'schools/school_form.html')

    def test_school_update_loads(self):
        """School update form should load for staff users."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('schools:update', kwargs={'pk': self.school.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'schools/school_form.html')
