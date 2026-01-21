from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from django.urls import reverse


class UserViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username="testsuperuser", password="adminpass123", email="testsuperuser@example.com"
        )
        self.staff_user = User.objects.create_user(username="staffuser", password="staffpass123", is_staff=True)
        # Create user admin group and user
        self.user_admin_group, _ = Group.objects.get_or_create(name="Brugeradministrator")
        self.user_admin = User.objects.create_user(username="useradmin", password="useradminpass123", is_staff=True)
        self.user_admin.groups.add(self.user_admin_group)

    def test_user_list_requires_permission(self):
        """User list should only be accessible to user admins."""
        # Staff user without permission should get 403
        self.client.login(username="staffuser", password="staffpass123")
        response = self.client.get(reverse("accounts:user-list"))
        self.assertEqual(response.status_code, 403)

    def test_user_list_loads_for_user_admin(self):
        """User list should load for users in Brugeradministrator group."""
        self.client.login(username="useradmin", password="useradminpass123")
        response = self.client.get(reverse("accounts:user-list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/user_list.html")

    def test_user_list_loads_for_superuser(self):
        """User list should load for superusers."""
        self.client.login(username="testsuperuser", password="adminpass123")
        response = self.client.get(reverse("accounts:user-list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/user_list.html")

    def test_user_create_loads(self):
        """User create form should load for superusers."""
        self.client.login(username="testsuperuser", password="adminpass123")
        response = self.client.get(reverse("accounts:user-create"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/user_form.html")

    def test_user_detail_loads(self):
        """User detail should load for superusers."""
        self.client.login(username="testsuperuser", password="adminpass123")
        response = self.client.get(reverse("accounts:user-detail", kwargs={"pk": self.staff_user.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/user_detail.html")


class AuthenticationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123")

    def test_login_page_loads(self):
        """Login page should load."""
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)

    def test_login_works(self):
        """User can log in with valid credentials."""
        response = self.client.post(reverse("login"), {"username": "testuser", "password": "testpass123"})
        self.assertEqual(response.status_code, 302)  # Redirect after login

    def test_logout_works(self):
        """User can log out."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, 302)  # Redirect after logout
