from datetime import datetime

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.schools.models import School

from .models import ContactTime


class ContactTimeModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.school = School.objects.create(
            name='Test School',
            location='Location',
            contact_name='Contact',
            contact_email='test@example.com'
        )

    def test_create_contact(self):
        """ContactTime model can be created."""
        contact = ContactTime.objects.create(
            school=self.school,
            created_by=self.user,
            contacted_at=timezone.now(),
            comment='Test comment'
        )
        self.assertEqual(contact.school, self.school)
        self.assertEqual(contact.created_by, self.user)

    def test_contact_without_user(self):
        """ContactTime can be created without a user (created_by is nullable)."""
        contact = ContactTime.objects.create(
            school=self.school,
            created_by=None,
            contacted_at=timezone.now(),
            comment='Test comment'
        )
        self.assertIsNone(contact.created_by)


class ContactViewTest(TestCase):
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
        self.contact = ContactTime.objects.create(
            school=self.school,
            created_by=self.user,
            contacted_at=timezone.now(),
            comment='Test comment'
        )

    def test_contact_list_loads(self):
        """Contact list should load for staff users."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('contacts:list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'contacts/contact_list.html')

    def test_contact_detail_loads(self):
        """Contact detail should load for staff users."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('contacts:detail', kwargs={'pk': self.contact.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'contacts/contact_detail.html')

    def test_contact_create_loads(self):
        """Contact create form should load for staff users."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('contacts:create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'contacts/contact_form.html')
