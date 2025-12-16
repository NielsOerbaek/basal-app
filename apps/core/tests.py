from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


class DashboardViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True
        )

    def test_dashboard_requires_login(self):
        """Dashboard should redirect unauthenticated users to login."""
        response = self.client.get(reverse('core:dashboard'))
        self.assertRedirects(response, '/login/?next=/')

    def test_dashboard_loads_for_staff(self):
        """Dashboard should load successfully for staff users."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/dashboard.html')
