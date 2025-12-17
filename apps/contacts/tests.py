from datetime import date, time

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

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
            adresse='Test Address',
            kommune='Test Kommune'
        )

    def test_create_contact(self):
        """ContactTime model can be created."""
        contact = ContactTime.objects.create(
            school=self.school,
            created_by=self.user,
            contacted_date=date.today(),
            contacted_time=time(10, 30),
            inbound=False,
            comment='Test comment'
        )
        self.assertEqual(contact.school, self.school)
        self.assertEqual(contact.created_by, self.user)
        self.assertEqual(contact.contacted_date, date.today())

    def test_contact_without_user(self):
        """ContactTime can be created without a user (created_by is nullable)."""
        contact = ContactTime.objects.create(
            school=self.school,
            created_by=None,
            contacted_date=date.today(),
            comment='Test comment'
        )
        self.assertIsNone(contact.created_by)

    def test_contact_time_optional(self):
        """ContactTime can be created without time."""
        contact = ContactTime.objects.create(
            school=self.school,
            contacted_date=date.today(),
            contacted_time=None,
            comment='Test comment'
        )
        self.assertIsNone(contact.contacted_time)


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
            adresse='Test Address',
            kommune='Test Kommune'
        )
        self.contact = ContactTime.objects.create(
            school=self.school,
            created_by=self.user,
            contacted_date=date.today(),
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
