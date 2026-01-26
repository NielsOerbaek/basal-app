from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import UserProfile


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


class UserProfileTest(TestCase):
    def test_userprofile_created_with_user(self):
        """UserProfile is auto-created when User is created."""
        user = User.objects.create_user(username="newuser", password="testpass")
        self.assertTrue(hasattr(user, "profile"))
        self.assertIsInstance(user.profile, UserProfile)

    def test_userprofile_default_notify_false(self):
        """UserProfile.notify_on_school_signup defaults to False."""
        user = User.objects.create_user(username="newuser", password="testpass")
        self.assertFalse(user.profile.notify_on_school_signup)

    def test_userprofile_str(self):
        """UserProfile __str__ returns username."""
        user = User.objects.create_user(username="testuser", password="testpass")
        self.assertEqual(str(user.profile), "testuser")


class UserFormNotificationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username="notifyadmin", password="adminpass", email="notifyadmin@example.com"
        )
        self.target_user = User.objects.create_user(
            username="notifytarget", password="targetpass", email="notifytarget@example.com"
        )

    def test_update_form_has_notification_field(self):
        """UserUpdateForm includes notify_on_school_signup field."""
        from apps.accounts.forms import UserUpdateForm

        form = UserUpdateForm(instance=self.target_user)
        self.assertIn("notify_on_school_signup", form.fields)

    def test_update_form_saves_notification_preference(self):
        """UserUpdateForm saves notify_on_school_signup to profile."""
        self.client.login(username="notifyadmin", password="adminpass")
        response = self.client.post(
            reverse("accounts:user-update", kwargs={"pk": self.target_user.pk}),
            {
                "username": "notifytarget",
                "first_name": "Target",
                "last_name": "User",
                "email": "notifytarget@example.com",
                "is_active": True,
                "notify_on_school_signup": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.target_user.refresh_from_db()
        self.assertTrue(self.target_user.profile.notify_on_school_signup)


class AccountSettingsViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="oldpassword123",
            first_name="Test",
            last_name="User",
        )
        self.client.login(username="testuser", password="oldpassword123")
        self.url = reverse("accounts:settings")

    def test_settings_page_requires_login(self):
        """Settings page redirects to login if not authenticated."""
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(response, f"/login/?next={self.url}")

    def test_settings_page_loads(self):
        """Settings page loads for authenticated user."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "testuser")

    def test_update_profile(self):
        """User can update their profile information."""
        response = self.client.post(
            self.url,
            {
                "form_type": "profile",
                "username": "newusername",
                "first_name": "New",
                "last_name": "Name",
                "email": "new@example.com",
            },
        )
        self.assertRedirects(response, self.url)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "newusername")
        self.assertEqual(self.user.first_name, "New")
        self.assertEqual(self.user.email, "new@example.com")

    def test_change_password(self):
        """User can change their password."""
        response = self.client.post(
            self.url,
            {
                "form_type": "password",
                "old_password": "oldpassword123",
                "new_password1": "newpassword456",
                "new_password2": "newpassword456",
            },
        )
        self.assertRedirects(response, self.url)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpassword456"))

    def test_change_password_wrong_old_password(self):
        """Password change fails with wrong old password."""
        response = self.client.post(
            self.url,
            {
                "form_type": "password",
                "old_password": "wrongpassword",
                "new_password1": "newpassword456",
                "new_password2": "newpassword456",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("oldpassword123"))

    def test_username_must_be_unique(self):
        """Cannot change username to one that already exists."""
        User.objects.create_user(username="existinguser", password="pass")
        response = self.client.post(
            self.url,
            {
                "form_type": "profile",
                "username": "existinguser",
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "testuser")
