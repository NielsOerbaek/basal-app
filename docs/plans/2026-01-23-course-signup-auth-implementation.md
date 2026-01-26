# Course Signup Authentication Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add authentication to course signup form with school-specific passwords and instant school enrollment.

**Architecture:** Schools get pronounceable passwords and URL tokens on enrollment. Course signup requires authentication via password, token URL, or staff login. UserProfile stores notification preferences for new school signups.

**Tech Stack:** Django 5.x, crispy-forms, HTMX, resend (email)

---

## Task 1: Add Password Generation Utilities

**Files:**
- Create: `apps/schools/utils.py`
- Test: `apps/schools/tests.py`

**Step 1: Write the failing test**

Add to `apps/schools/tests.py`:

```python
class PasswordGenerationTest(TestCase):
    def test_generate_pronounceable_password_length(self):
        """Pronounceable password has correct length (2 chars per syllable)."""
        from apps.schools.utils import generate_pronounceable_password
        password = generate_pronounceable_password(syllables=4)
        self.assertEqual(len(password), 8)

    def test_generate_pronounceable_password_pattern(self):
        """Pronounceable password alternates consonants and vowels."""
        from apps.schools.utils import generate_pronounceable_password
        password = generate_pronounceable_password(syllables=4)
        consonants = 'bdfgklmnprstvz'
        vowels = 'aeiou'
        for i, char in enumerate(password):
            if i % 2 == 0:
                self.assertIn(char, consonants)
            else:
                self.assertIn(char, vowels)

    def test_generate_token_length(self):
        """Token has correct length."""
        from apps.schools.utils import generate_signup_token
        token = generate_signup_token()
        self.assertEqual(len(token), 32)

    def test_generate_token_alphanumeric(self):
        """Token contains only alphanumeric characters."""
        from apps.schools.utils import generate_signup_token
        token = generate_signup_token()
        self.assertTrue(token.isalnum())
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/schools/tests.py::PasswordGenerationTest -v`
Expected: FAIL with "No module named 'apps.schools.utils'" or similar

**Step 3: Write minimal implementation**

Create `apps/schools/utils.py`:

```python
import secrets
import string

CONSONANTS = 'bdfgklmnprstvz'
VOWELS = 'aeiou'


def generate_pronounceable_password(syllables=4):
    """Generate a pronounceable password like 'bafimoku'.

    Args:
        syllables: Number of consonant-vowel pairs (default 4 = 8 chars)

    Returns:
        Lowercase pronounceable password
    """
    password = ''
    for _ in range(syllables):
        password += secrets.choice(CONSONANTS)
        password += secrets.choice(VOWELS)
    return password


def generate_signup_token(length=32):
    """Generate a random alphanumeric token for URL-based auth.

    Args:
        length: Token length (default 32)

    Returns:
        Alphanumeric token string
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))
```

**Step 4: Run test to verify it passes**

Run: `pytest apps/schools/tests.py::PasswordGenerationTest -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/schools/utils.py apps/schools/tests.py
git commit -m "$(cat <<'EOF'
feat(schools): add password and token generation utilities

Add generate_pronounceable_password() for human-readable passwords
and generate_signup_token() for URL-based authentication.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Add Password/Token Fields to School Model

**Files:**
- Modify: `apps/schools/models.py`
- Create: `apps/schools/migrations/XXXX_add_signup_credentials.py` (auto-generated)
- Test: `apps/schools/tests.py`

**Step 1: Write the failing test**

Add to `apps/schools/tests.py`:

```python
class SchoolCredentialsTest(TestCase):
    def test_school_has_signup_password_field(self):
        """School model has signup_password field."""
        school = School.objects.create(
            name='Test School',
            adresse='Test Address',
            kommune='Test Kommune',
        )
        self.assertEqual(school.signup_password, '')

    def test_school_has_signup_token_field(self):
        """School model has signup_token field."""
        school = School.objects.create(
            name='Test School',
            adresse='Test Address',
            kommune='Test Kommune',
        )
        self.assertEqual(school.signup_token, '')

    def test_generate_credentials(self):
        """School.generate_credentials() creates password and token."""
        school = School.objects.create(
            name='Test School',
            adresse='Test Address',
            kommune='Test Kommune',
        )
        school.generate_credentials()
        self.assertEqual(len(school.signup_password), 8)
        self.assertEqual(len(school.signup_token), 32)

    def test_generate_credentials_saves(self):
        """School.generate_credentials() saves to database."""
        school = School.objects.create(
            name='Test School',
            adresse='Test Address',
            kommune='Test Kommune',
        )
        school.generate_credentials()
        school.refresh_from_db()
        self.assertEqual(len(school.signup_password), 8)
        self.assertEqual(len(school.signup_token), 32)
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/schools/tests.py::SchoolCredentialsTest -v`
Expected: FAIL with attribute error

**Step 3: Write minimal implementation**

Edit `apps/schools/models.py`, add fields to School class after `updated_at`:

```python
    signup_password = models.CharField(
        max_length=20, blank=True, verbose_name="Tilmeldingskode",
        help_text="Kode til kursustilmelding"
    )
    signup_token = models.CharField(
        max_length=32, blank=True, db_index=True, verbose_name="Tilmeldingstoken",
        help_text="Token til direkte link"
    )
```

Add method to School class:

```python
    def generate_credentials(self):
        """Generate signup password and token for this school."""
        from apps.schools.utils import generate_pronounceable_password, generate_signup_token
        self.signup_password = generate_pronounceable_password()
        self.signup_token = generate_signup_token()
        self.save(update_fields=['signup_password', 'signup_token'])
```

**Step 4: Create and run migration**

Run: `python manage.py makemigrations schools --name add_signup_credentials`
Run: `python manage.py migrate`

**Step 5: Run test to verify it passes**

Run: `pytest apps/schools/tests.py::SchoolCredentialsTest -v`
Expected: PASS

**Step 6: Commit**

```bash
git add apps/schools/models.py apps/schools/migrations/
git commit -m "$(cat <<'EOF'
feat(schools): add signup_password and signup_token fields

Schools can now have credentials for course signup authentication.
- signup_password: pronounceable password for manual entry
- signup_token: random token for URL-based auth
- generate_credentials(): method to create both

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Add UserProfile Model with Notification Preference

**Files:**
- Modify: `apps/accounts/models.py`
- Create: `apps/accounts/migrations/XXXX_add_userprofile.py` (auto-generated)
- Test: `apps/accounts/tests.py`

**Step 1: Write the failing test**

Add to `apps/accounts/tests.py`:

```python
from apps.accounts.models import UserProfile


class UserProfileTest(TestCase):
    def test_userprofile_created_with_user(self):
        """UserProfile is auto-created when User is created."""
        user = User.objects.create_user(username='newuser', password='testpass')
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsInstance(user.profile, UserProfile)

    def test_userprofile_default_notify_false(self):
        """UserProfile.notify_on_school_signup defaults to False."""
        user = User.objects.create_user(username='newuser', password='testpass')
        self.assertFalse(user.profile.notify_on_school_signup)

    def test_userprofile_str(self):
        """UserProfile __str__ returns username."""
        user = User.objects.create_user(username='testuser', password='testpass')
        self.assertEqual(str(user.profile), 'testuser')
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/accounts/tests.py::UserProfileTest -v`
Expected: FAIL with ImportError

**Step 3: Write minimal implementation**

Replace contents of `apps/accounts/models.py`:

```python
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """Extended user profile for notification preferences."""
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile'
    )
    notify_on_school_signup = models.BooleanField(
        default=False,
        verbose_name="Modtag email ved ny skoletilmelding",
        help_text="Få besked når en ny skole tilmelder sig Basal"
    )

    class Meta:
        verbose_name = "Brugerprofil"
        verbose_name_plural = "Brugerprofiler"

    def __str__(self):
        return self.user.username


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile when User is created."""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Ensure UserProfile exists and is saved."""
    if not hasattr(instance, 'profile'):
        UserProfile.objects.create(user=instance)
```

**Step 4: Create and run migration**

Run: `python manage.py makemigrations accounts --name add_userprofile`
Run: `python manage.py migrate`

**Step 5: Create profiles for existing users**

Run: `python manage.py shell -c "from django.contrib.auth.models import User; from apps.accounts.models import UserProfile; [UserProfile.objects.get_or_create(user=u) for u in User.objects.all()]"`

**Step 6: Run test to verify it passes**

Run: `pytest apps/accounts/tests.py::UserProfileTest -v`
Expected: PASS

**Step 7: Commit**

```bash
git add apps/accounts/models.py apps/accounts/migrations/
git commit -m "$(cat <<'EOF'
feat(accounts): add UserProfile model with notification preference

- UserProfile auto-created via signal when User is created
- notify_on_school_signup field for school enrollment notifications
- Backfilled profiles for existing users

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Add Notification Checkbox to User Forms

**Files:**
- Modify: `apps/accounts/forms.py`
- Modify: `apps/accounts/views.py`
- Test: `apps/accounts/tests.py`

**Step 1: Write the failing test**

Add to `apps/accounts/tests.py`:

```python
class UserFormNotificationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username='admin', password='adminpass', email='admin@example.com'
        )
        self.target_user = User.objects.create_user(
            username='targetuser', password='targetpass', email='target@example.com'
        )

    def test_update_form_has_notification_field(self):
        """UserUpdateForm includes notify_on_school_signup field."""
        from apps.accounts.forms import UserUpdateForm
        form = UserUpdateForm(instance=self.target_user)
        self.assertIn('notify_on_school_signup', form.fields)

    def test_update_form_saves_notification_preference(self):
        """UserUpdateForm saves notify_on_school_signup to profile."""
        self.client.login(username='admin', password='adminpass')
        response = self.client.post(
            reverse('accounts:user-update', kwargs={'pk': self.target_user.pk}),
            {
                'username': 'targetuser',
                'first_name': 'Target',
                'last_name': 'User',
                'email': 'target@example.com',
                'is_active': True,
                'notify_on_school_signup': True,
            }
        )
        self.assertEqual(response.status_code, 302)
        self.target_user.refresh_from_db()
        self.assertTrue(self.target_user.profile.notify_on_school_signup)
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/accounts/tests.py::UserFormNotificationTest -v`
Expected: FAIL with KeyError or assertion error

**Step 3: Write minimal implementation**

Edit `apps/accounts/forms.py`:

Add field to `UserUpdateForm` class (after other fields):

```python
    notify_on_school_signup = forms.BooleanField(
        label="Modtag email ved ny skoletilmelding",
        required=False,
        help_text="Få besked når en ny skole tilmelder sig Basal",
    )
```

Update `__init__` method to set initial value:

```python
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial permission values based on current user state
        if self.instance and self.instance.pk:
            perms = self._get_permissions(self.instance)
            self.fields["is_user_admin"].initial = perms["is_user_admin"]
            self.fields["is_signup_admin"].initial = perms["is_signup_admin"]
            self.fields["is_full_admin"].initial = perms["is_full_admin"]
            # Set notification preference from profile
            if hasattr(self.instance, 'profile'):
                self.fields["notify_on_school_signup"].initial = self.instance.profile.notify_on_school_signup

        self.helper = FormHelper()
        self.helper.layout = Layout(
            "username",
            Row(
                Column("first_name", css_class="col-md-6"),
                Column("last_name", css_class="col-md-6"),
            ),
            "email",
            "is_active",
            HTML("<hr><h5>Rettigheder</h5>"),
            "is_user_admin",
            "is_signup_admin",
            "is_full_admin",
            HTML("<hr><h5>Notifikationer</h5>"),
            "notify_on_school_signup",
            Submit("submit", "Gem ændringer", css_class="btn btn-primary mt-3"),
        )
```

Update `save` method:

```python
    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            self._apply_permissions(
                user,
                self.cleaned_data.get("is_user_admin", False),
                self.cleaned_data.get("is_signup_admin", False),
                self.cleaned_data.get("is_full_admin", False),
            )
            # Save notification preference to profile
            if hasattr(user, 'profile'):
                user.profile.notify_on_school_signup = self.cleaned_data.get("notify_on_school_signup", False)
                user.profile.save()
        return user
```

**Step 4: Run test to verify it passes**

Run: `pytest apps/accounts/tests.py::UserFormNotificationTest -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/accounts/forms.py
git commit -m "$(cat <<'EOF'
feat(accounts): add notification checkbox to user update form

Users can now opt-in to receive email notifications when new schools
sign up for Basal.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Add Email Services for School Enrollment

**Files:**
- Modify: `apps/emails/services.py`
- Test: `apps/emails/tests.py` (create if needed)

**Step 1: Write the failing test**

Create `apps/emails/tests.py`:

```python
from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from apps.schools.models import School
from apps.accounts.models import UserProfile


class SchoolEnrollmentEmailTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name='Test School',
            adresse='Test Address',
            kommune='Test Kommune',
            signup_password='bafimoku',
            signup_token='abc123token',
        )

    @override_settings(RESEND_API_KEY=None)
    def test_send_enrollment_confirmation_returns_true(self):
        """send_school_enrollment_confirmation returns True in dev mode."""
        from apps.emails.services import send_school_enrollment_confirmation
        result = send_school_enrollment_confirmation(
            self.school,
            contact_email='test@example.com',
            contact_name='Test Person'
        )
        self.assertTrue(result)


class SchoolSignupNotificationTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name='Test School',
            adresse='Test Address',
            kommune='Test Kommune',
        )
        # Create user with notification enabled
        self.user = User.objects.create_user(
            username='notifyuser',
            email='notify@example.com',
            password='testpass'
        )
        self.user.profile.notify_on_school_signup = True
        self.user.profile.save()

    @override_settings(RESEND_API_KEY=None)
    def test_send_notification_to_subscribed_users(self):
        """send_school_signup_notifications sends to subscribed users."""
        from apps.emails.services import send_school_signup_notifications
        result = send_school_signup_notifications(
            self.school,
            contact_name='Test Contact',
            contact_email='contact@school.dk'
        )
        self.assertEqual(result, 1)  # One user notified

    @override_settings(RESEND_API_KEY=None)
    def test_no_notification_when_no_subscribers(self):
        """send_school_signup_notifications returns 0 when no subscribers."""
        self.user.profile.notify_on_school_signup = False
        self.user.profile.save()

        from apps.emails.services import send_school_signup_notifications
        result = send_school_signup_notifications(
            self.school,
            contact_name='Test Contact',
            contact_email='contact@school.dk'
        )
        self.assertEqual(result, 0)
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/emails/tests.py -v`
Expected: FAIL with ImportError

**Step 3: Write minimal implementation**

Add to `apps/emails/services.py`:

```python
def send_school_enrollment_confirmation(school, contact_email, contact_name):
    """
    Send enrollment confirmation email to school contact.

    Args:
        school: School instance with credentials
        contact_email: Email address of contact person
        contact_name: Name of contact person

    Returns:
        True if successful, False otherwise
    """
    subject = f"Velkommen til Basal - {school.name}"

    signup_url = f"{settings.SITE_URL}/signup/course/?token={school.signup_token}"

    body_html = f"""
    <p>Hej {contact_name},</p>

    <p>Tak for jeres tilmelding til Basal! {school.name} er nu tilmeldt.</p>

    <h3>Tilmelding til kurser</h3>
    <p>I kan nu tilmelde jer kurser på to måder:</p>

    <ol>
        <li><strong>Via direkte link:</strong><br>
            <a href="{signup_url}">{signup_url}</a></li>
        <li><strong>Via kode:</strong><br>
            Gå til {settings.SITE_URL}/signup/course/ og indtast koden: <strong>{school.signup_password}</strong></li>
    </ol>

    <p>Med venlig hilsen,<br>Basal</p>
    """

    if not getattr(settings, 'RESEND_API_KEY', None):
        logger.info(f"[EMAIL] To: {contact_email}")
        logger.info(f"[EMAIL] Subject: {subject}")
        logger.info(f"[EMAIL] Body: {body_html[:200]}...")
        return True

    try:
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": [contact_email],
            "subject": subject,
            "html": body_html,
        })
        return True
    except Exception as e:
        logger.error(f"Failed to send enrollment confirmation: {e}")
        return False


def send_school_signup_notifications(school, contact_name, contact_email):
    """
    Send notification emails to staff users who opted in.

    Args:
        school: School instance that signed up
        contact_name: Name of school contact person
        contact_email: Email of school contact person

    Returns:
        Number of notifications sent
    """
    from django.contrib.auth.models import User
    from apps.accounts.models import UserProfile

    # Get users with notification enabled
    subscribed_profiles = UserProfile.objects.filter(
        notify_on_school_signup=True,
        user__email__isnull=False
    ).exclude(user__email='').select_related('user')

    if not subscribed_profiles:
        return 0

    subject = f"Ny skoletilmelding: {school.name}"
    school_url = f"{settings.SITE_URL}/schools/{school.pk}/"

    body_html = f"""
    <p>En ny skole har tilmeldt sig Basal:</p>

    <ul>
        <li><strong>Skole:</strong> {school.name}</li>
        <li><strong>Kommune:</strong> {school.kommune}</li>
        <li><strong>Kontaktperson:</strong> {contact_name} ({contact_email})</li>
    </ul>

    <p><a href="{school_url}">Se skolen i Basal</a></p>
    """

    count = 0
    for profile in subscribed_profiles:
        if not getattr(settings, 'RESEND_API_KEY', None):
            logger.info(f"[EMAIL] Notification to: {profile.user.email}")
            logger.info(f"[EMAIL] Subject: {subject}")
            count += 1
            continue

        try:
            resend.api_key = settings.RESEND_API_KEY
            resend.Emails.send({
                "from": settings.DEFAULT_FROM_EMAIL,
                "to": [profile.user.email],
                "subject": subject,
                "html": body_html,
            })
            count += 1
        except Exception as e:
            logger.error(f"Failed to send notification to {profile.user.email}: {e}")

    return count
```

**Step 4: Run test to verify it passes**

Run: `pytest apps/emails/tests.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/emails/services.py apps/emails/tests.py
git commit -m "$(cat <<'EOF'
feat(emails): add school enrollment confirmation and notification emails

- send_school_enrollment_confirmation(): sends password and link to school
- send_school_signup_notifications(): notifies subscribed staff users

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Rewrite School Signup View for Instant Enrollment

**Files:**
- Modify: `apps/signups/views.py`
- Modify: `apps/signups/forms.py`
- Test: `apps/signups/tests.py`

**Step 1: Write the failing test**

Update tests in `apps/signups/tests.py` - replace `SchoolSignupViewTest`:

```python
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

    def test_school_signup_enrolls_existing_school(self):
        """School signup with existing school sets enrolled_at and generates credentials."""
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
        self.school.refresh_from_db()
        self.assertIsNotNone(self.school.enrolled_at)
        self.assertEqual(len(self.school.signup_password), 8)
        self.assertEqual(len(self.school.signup_token), 32)

    def test_school_signup_creates_new_school(self):
        """School signup with new school name creates school with credentials."""
        response = self.client.post(
            reverse("signup:school"),
            {
                "municipality": "New Kommune",
                "school_not_listed": "on",
                "new_school_name": "Brand New School",
                "new_school_address": "New Address 123",
                "contact_name": "Test Contact",
                "contact_email": "contact@school.dk",
            },
        )
        self.assertRedirects(response, reverse("signup:school-success"))
        new_school = School.objects.get(name="Brand New School")
        self.assertIsNotNone(new_school.enrolled_at)
        self.assertEqual(new_school.kommune, "New Kommune")
        self.assertEqual(new_school.adresse, "New Address 123")
        self.assertEqual(len(new_school.signup_password), 8)

    def test_school_signup_success_loads(self):
        """School signup success page should load."""
        response = self.client.get(reverse("signup:school-success"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "signups/school_signup_success.html")
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/signups/tests.py::SchoolSignupViewTest -v`
Expected: FAIL (enrolled_at not set, credentials not generated)

**Step 3: Write minimal implementation**

Update `apps/signups/forms.py` - add address field to `SchoolSignupForm`:

```python
    new_school_address = forms.CharField(
        max_length=255,
        required=False,
        label="Skolens adresse",
    )
```

Update layout in `__init__` to include new field:

```python
            Div("new_school_name", "new_school_address", css_id="new-school-fields", style="display: none;"),
```

Update `clean` method:

```python
    def clean(self):
        cleaned_data = super().clean()
        school_not_listed = cleaned_data.get("school_not_listed")
        school = cleaned_data.get("school")
        new_school_name = cleaned_data.get("new_school_name")
        new_school_address = cleaned_data.get("new_school_address")

        if school_not_listed:
            if not new_school_name:
                raise ValidationError({"new_school_name": "Angiv venligst skolens navn."})
            if not new_school_address:
                raise ValidationError({"new_school_address": "Angiv venligst skolens adresse."})
        else:
            if not school:
                raise ValidationError({"school": "Vælg venligst en skole eller marker at din skole ikke er på listen."})

        return cleaned_data
```

Update `apps/signups/views.py` - rewrite `SchoolSignupView.post`:

```python
    def post(self, request):
        from datetime import date
        from apps.emails.services import send_school_enrollment_confirmation, send_school_signup_notifications

        page = self.get_signup_page()
        if page and not page.is_active:
            return render(request, "signups/page_unavailable.html", {"page": page})

        form = SchoolSignupForm(request.POST, request.FILES, signup_page=page)
        if form.is_valid():
            contact_name = form.cleaned_data["contact_name"]
            contact_email = form.cleaned_data["contact_email"]
            municipality = form.cleaned_data["municipality"]

            if form.cleaned_data.get("school_not_listed"):
                # Create new school
                school = School.objects.create(
                    name=form.cleaned_data["new_school_name"],
                    adresse=form.cleaned_data.get("new_school_address", ""),
                    kommune=municipality,
                    enrolled_at=date.today(),
                )
            else:
                # Use existing school
                school = form.cleaned_data["school"]
                if not school.enrolled_at:
                    school.enrolled_at = date.today()
                    school.save(update_fields=["enrolled_at"])

            # Generate credentials
            school.generate_credentials()

            # Create contact person
            from apps.schools.models import Person, PersonRole
            Person.objects.create(
                school=school,
                name=contact_name,
                email=contact_email,
                phone=form.cleaned_data.get("contact_phone", ""),
                role=PersonRole.KOORDINATOR,
                is_primary=True,
            )

            # Send confirmation email
            send_school_enrollment_confirmation(school, contact_email, contact_name)

            # Notify subscribed users
            send_school_signup_notifications(school, contact_name, contact_email)

            return redirect("signup:school-success")

        return render(request, self.template_name, {"form": form, "page": page})
```

**Step 4: Run test to verify it passes**

Run: `pytest apps/signups/tests.py::SchoolSignupViewTest -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/signups/views.py apps/signups/forms.py
git commit -m "$(cat <<'EOF'
feat(signups): instant school enrollment with credentials

School signup now:
- Immediately sets enrolled_at (no admin processing)
- Generates password and token
- Creates contact person
- Sends confirmation email with credentials
- Notifies subscribed staff users

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Add Password Validation Endpoint for Course Signup

**Files:**
- Modify: `apps/signups/views.py`
- Modify: `apps/signups/urls.py`
- Test: `apps/signups/tests.py`

**Step 1: Write the failing test**

Add to `apps/signups/tests.py`:

```python
class ValidateSchoolPasswordViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
            enrolled_at=date.today(),
            signup_password="bafimoku",
            signup_token="abc123tokenxyz",
        )

    def test_valid_password_returns_school_id(self):
        """Valid password returns school ID and sets session."""
        response = self.client.post(
            reverse("signup:validate-password"),
            {"password": "bafimoku"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["valid"])
        self.assertEqual(data["school_id"], self.school.pk)
        self.assertEqual(data["school_name"], "Test School")

    def test_invalid_password_returns_error(self):
        """Invalid password returns error."""
        response = self.client.post(
            reverse("signup:validate-password"),
            {"password": "wrongpass"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["valid"])

    def test_password_sets_session(self):
        """Valid password sets session variable."""
        self.client.post(
            reverse("signup:validate-password"),
            {"password": "bafimoku"},
            content_type="application/json",
        )
        session = self.client.session
        self.assertEqual(session.get("course_signup_school_id"), self.school.pk)
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/signups/tests.py::ValidateSchoolPasswordViewTest -v`
Expected: FAIL with NoReverseMatch

**Step 3: Write minimal implementation**

Add to `apps/signups/views.py`:

```python
import json

class ValidateSchoolPasswordView(View):
    """AJAX endpoint to validate school password and set session."""

    def post(self, request):
        try:
            data = json.loads(request.body)
            password = data.get("password", "").strip().lower()
        except (json.JSONDecodeError, AttributeError):
            password = request.POST.get("password", "").strip().lower()

        if not password:
            return JsonResponse({"valid": False, "error": "Indtast venligst en kode"})

        try:
            school = School.objects.get(
                signup_password__iexact=password,
                enrolled_at__isnull=False,
                opted_out_at__isnull=True,
            )
            # Store in session
            request.session["course_signup_school_id"] = school.pk
            return JsonResponse({
                "valid": True,
                "school_id": school.pk,
                "school_name": school.name,
            })
        except School.DoesNotExist:
            return JsonResponse({"valid": False, "error": "Ugyldig kode"})
```

Add to `apps/signups/urls.py`:

```python
    path("course/validate-password/", views.ValidateSchoolPasswordView.as_view(), name="validate-password"),
```

**Step 4: Run test to verify it passes**

Run: `pytest apps/signups/tests.py::ValidateSchoolPasswordViewTest -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/signups/views.py apps/signups/urls.py
git commit -m "$(cat <<'EOF'
feat(signups): add password validation endpoint for course signup

POST /signup/course/validate-password/ validates school password
and stores school ID in session for course signup authentication.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Add Authentication to Course Signup View

**Files:**
- Modify: `apps/signups/views.py`
- Test: `apps/signups/tests.py`

**Step 1: Write the failing test**

Add to `apps/signups/tests.py`:

```python
class CourseSignupAuthTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
            enrolled_at=date.today(),
            signup_password="bafimoku",
            signup_token="abc123tokenxyz456",
        )
        self.course = Course.objects.create(
            title="Test Course",
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=7),
            location="Test Location",
            is_published=True,
        )
        self.staff_user = User.objects.create_user(
            username="staffuser", password="staffpass", is_staff=True
        )

    def test_unauthenticated_shows_password_form(self):
        """Unauthenticated user sees password entry form."""
        response = self.client.get(reverse("signup:course"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="password-section"')
        self.assertContains(response, 'style="display: none;"')  # Form hidden

    def test_valid_token_shows_form_with_locked_school(self):
        """Valid token in URL shows form with school pre-selected."""
        response = self.client.get(
            reverse("signup:course") + "?token=abc123tokenxyz456"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test School")
        # Check session was set
        self.assertEqual(
            self.client.session.get("course_signup_school_id"),
            self.school.pk
        )

    def test_invalid_token_shows_error(self):
        """Invalid token shows error message."""
        response = self.client.get(
            reverse("signup:course") + "?token=invalidtoken"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ugyldigt link")

    def test_staff_user_sees_full_form(self):
        """Staff user sees form with school dropdown (not locked)."""
        self.client.login(username="staffuser", password="staffpass")
        response = self.client.get(reverse("signup:course"))
        self.assertEqual(response.status_code, 200)
        # Should NOT have password section
        self.assertNotContains(response, 'id="password-section"')

    def test_session_auth_shows_locked_form(self):
        """User with session auth sees form with locked school."""
        session = self.client.session
        session["course_signup_school_id"] = self.school.pk
        session.save()

        response = self.client.get(reverse("signup:course"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test School")
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/signups/tests.py::CourseSignupAuthTest -v`
Expected: FAIL (password section doesn't exist yet)

**Step 3: Write minimal implementation**

Update `CourseSignupView` in `apps/signups/views.py`:

```python
class CourseSignupView(View):
    """Public course signup form with authentication."""

    template_name = "signups/course_signup.html"

    def get_signup_page(self):
        try:
            return SignupPage.objects.prefetch_related("form_fields").get(page_type=SignupPageType.COURSE_SIGNUP)
        except SignupPage.DoesNotExist:
            return None

    def get_auth_context(self, request):
        """Determine authentication state and return context."""
        # Staff bypass - full access
        if request.user.is_authenticated and request.user.is_staff:
            return {
                "auth_mode": "staff",
                "locked_school": None,
                "show_password_form": False,
                "auth_error": None,
            }

        # Check for token in URL
        token = request.GET.get("token", "").strip()
        if token:
            try:
                school = School.objects.get(
                    signup_token=token,
                    enrolled_at__isnull=False,
                    opted_out_at__isnull=True,
                )
                request.session["course_signup_school_id"] = school.pk
                return {
                    "auth_mode": "token",
                    "locked_school": school,
                    "show_password_form": False,
                    "auth_error": None,
                }
            except School.DoesNotExist:
                return {
                    "auth_mode": None,
                    "locked_school": None,
                    "show_password_form": True,
                    "auth_error": "Ugyldigt link. Brug venligst koden fra jeres velkomstmail.",
                }

        # Check session
        school_id = request.session.get("course_signup_school_id")
        if school_id:
            try:
                school = School.objects.get(
                    pk=school_id,
                    enrolled_at__isnull=False,
                    opted_out_at__isnull=True,
                )
                return {
                    "auth_mode": "session",
                    "locked_school": school,
                    "show_password_form": False,
                    "auth_error": None,
                }
            except School.DoesNotExist:
                del request.session["course_signup_school_id"]

        # Not authenticated
        return {
            "auth_mode": None,
            "locked_school": None,
            "show_password_form": True,
            "auth_error": None,
        }

    def get(self, request):
        page = self.get_signup_page()
        if page and not page.is_active:
            return render(request, "signups/page_unavailable.html", {"page": page})

        auth_context = self.get_auth_context(request)
        form = CourseSignupForm(signup_page=page, locked_school=auth_context.get("locked_school"))

        return render(request, self.template_name, {
            "form": form,
            "page": page,
            **auth_context,
        })

    def post(self, request):
        page = self.get_signup_page()
        if page and not page.is_active:
            return render(request, "signups/page_unavailable.html", {"page": page})

        auth_context = self.get_auth_context(request)

        # Must be authenticated to submit
        if auth_context["show_password_form"] and not auth_context["locked_school"]:
            return render(request, self.template_name, {
                "form": CourseSignupForm(signup_page=page),
                "page": page,
                **auth_context,
                "auth_error": "Indtast venligst jeres skolekode først.",
            })

        form = CourseSignupForm(
            request.POST, request.FILES,
            signup_page=page,
            locked_school=auth_context.get("locked_school")
        )

        # Extract participant data from POST
        participants = self._extract_participants(request.POST)

        if not participants:
            return render(
                request,
                self.template_name,
                {"form": form, "page": page, "participant_error": "Mindst én deltager er påkrævet.", **auth_context},
            )

        for i, p in enumerate(participants):
            if not p.get("name") or not p.get("email"):
                return render(
                    request,
                    self.template_name,
                    {"form": form, "page": page, "participant_error": f"Deltager {i + 1} mangler navn eller e-mail.", **auth_context},
                )

        if form.is_valid():
            from apps.emails.services import send_signup_confirmation

            course = form.cleaned_data["course"]
            school = form.cleaned_data["school"]

            for participant in participants:
                signup = CourseSignUp.objects.create(
                    course=course,
                    school=school,
                    participant_name=participant["name"],
                    participant_email=participant["email"],
                    participant_title=participant.get("title", ""),
                    is_underviser=participant.get("is_underviser", True),
                )
                send_signup_confirmation(signup)

            return redirect("signup:course-success")

        return render(request, self.template_name, {"form": form, "page": page, **auth_context})

    def _extract_participants(self, post_data):
        """Extract participant data from POST data with indexed field names."""
        participants = []
        index = 0

        while True:
            name_key = f"participant_name_{index}"
            email_key = f"participant_email_{index}"
            title_key = f"participant_title_{index}"
            is_underviser_key = f"participant_is_underviser_{index}"

            if name_key not in post_data:
                break

            name = post_data.get(name_key, "").strip()
            email = post_data.get(email_key, "").strip()
            title = post_data.get(title_key, "").strip()
            is_underviser = is_underviser_key in post_data

            if name or email:
                participants.append({
                    "name": name,
                    "email": email,
                    "title": title,
                    "is_underviser": is_underviser,
                })

            index += 1

        return participants
```

Update `CourseSignupForm` in `apps/signups/forms.py` to accept locked_school:

```python
class CourseSignupForm(DynamicFieldsMixin, forms.Form):
    """Public course signup form with dynamic fields support."""

    course = CourseChoiceField(queryset=Course.objects.none(), label="Vælg et kursus", empty_label="Vælg et kursus...")
    school = SchoolChoiceField(queryset=School.objects.none(), label="Vælg din skole", empty_label="Vælg en skole...")

    def __init__(self, *args, signup_page=None, locked_school=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.locked_school = locked_school

        # Set querysets
        self.fields["course"].queryset = Course.objects.filter(
            is_published=True, start_date__gte=timezone.now().date()
        ).order_by("start_date")

        if locked_school:
            # Lock to specific school
            self.fields["school"].queryset = School.objects.filter(pk=locked_school.pk)
            self.fields["school"].initial = locked_school
            self.fields["school"].widget.attrs["disabled"] = True
        else:
            self.fields["school"].queryset = (
                School.objects.active().filter(enrolled_at__isnull=False, opted_out_at__isnull=True).order_by("name")
            )

        # ... rest of __init__ unchanged
```

Also update clean method to handle locked school:

```python
    def clean_school(self):
        # If school is locked, use the locked school
        if self.locked_school:
            return self.locked_school
        return self.cleaned_data.get("school")
```

**Step 4: Run test to verify it passes**

Run: `pytest apps/signups/tests.py::CourseSignupAuthTest -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/signups/views.py apps/signups/forms.py
git commit -m "$(cat <<'EOF'
feat(signups): add authentication to course signup view

Course signup now supports three auth modes:
- Token URL: ?token=xxx pre-selects and locks school
- Password: validates via AJAX, stores in session
- Staff: bypasses auth, can select any school

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Update Course Signup Template with Password Form

**Files:**
- Modify: `apps/signups/templates/signups/course_signup.html`

**Step 1: Update template**

Update `apps/signups/templates/signups/course_signup.html` to add password section:

After the intro_text section and before the form errors, add:

```html
{% if show_password_form %}
<div id="password-section" class="card mb-4">
    <div class="card-body">
        <h5 class="card-title">Indtast skolekode</h5>
        <p class="text-muted">Indtast koden fra jeres velkomstmail for at tilmelde deltagere.</p>

        {% if auth_error %}
        <div class="alert alert-danger">{{ auth_error }}</div>
        {% endif %}

        <div class="input-group mb-3">
            <input type="text" id="school-password" class="form-control form-control-lg"
                   placeholder="Indtast kode..." autocomplete="off">
            <button type="button" id="validate-password-btn" class="btn btn-primary btn-lg">
                <i class="bi bi-arrow-right"></i>
            </button>
        </div>
        <div id="password-error" class="text-danger" style="display: none;"></div>
        <div id="password-success" class="text-success" style="display: none;"></div>
    </div>
</div>
{% endif %}

{% if locked_school %}
<div class="alert alert-info mb-4">
    <i class="bi bi-building me-2"></i>
    Du tilmelder deltagere fra <strong>{{ locked_school.name }}</strong>
    {% if auth_mode != 'staff' %}
    <a href="{% url 'signup:course' %}" class="float-end">Skift skole</a>
    {% endif %}
</div>
{% endif %}
```

Update the form section to conditionally show/hide:

```html
<div id="signup-form-container" {% if show_password_form %}style="display: none;"{% endif %}>
    {# existing form content #}
</div>
```

Add JavaScript for password validation at the end of `signup_extra_js`:

```javascript
// Password validation
const passwordSection = document.getElementById('password-section');
const passwordInput = document.getElementById('school-password');
const validateBtn = document.getElementById('validate-password-btn');
const passwordError = document.getElementById('password-error');
const passwordSuccess = document.getElementById('password-success');
const formContainer = document.getElementById('signup-form-container');

if (validateBtn) {
    validateBtn.addEventListener('click', validatePassword);
    passwordInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            validatePassword();
        }
    });
}

function validatePassword() {
    const password = passwordInput.value.trim();
    if (!password) {
        passwordError.textContent = 'Indtast venligst en kode';
        passwordError.style.display = 'block';
        return;
    }

    validateBtn.disabled = true;
    passwordError.style.display = 'none';

    fetch('{% url "signup:validate-password" %}', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify({ password: password })
    })
    .then(response => response.json())
    .then(data => {
        validateBtn.disabled = false;
        if (data.valid) {
            passwordSuccess.textContent = 'Kode accepteret! Indlæser...';
            passwordSuccess.style.display = 'block';
            // Reload page to show form with locked school
            window.location.reload();
        } else {
            passwordError.textContent = data.error || 'Ugyldig kode';
            passwordError.style.display = 'block';
        }
    })
    .catch(() => {
        validateBtn.disabled = false;
        passwordError.textContent = 'Der opstod en fejl. Prøv igen.';
        passwordError.style.display = 'block';
    });
}
```

**Step 2: Run tests to verify existing functionality**

Run: `pytest apps/signups/tests.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add apps/signups/templates/signups/course_signup.html
git commit -m "$(cat <<'EOF'
feat(signups): update course signup template with password form

- Adds password entry section when not authenticated
- Shows locked school info when authenticated
- AJAX password validation with feedback

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Add Credentials Section to School Detail Page

**Files:**
- Modify: `apps/schools/templates/schools/school_detail.html`
- Modify: `apps/schools/views.py`
- Modify: `apps/schools/urls.py`
- Test: `apps/schools/tests.py`

**Step 1: Write the failing test**

Add to `apps/schools/tests.py`:

```python
class SchoolCredentialsViewTest(TestCase):
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
            enrolled_at=date.today(),
            signup_password='bafimoku',
            signup_token='abc123token',
        )

    def test_detail_shows_credentials_for_enrolled(self):
        """School detail shows credentials section for enrolled schools."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('schools:detail', kwargs={'pk': self.school.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tilmeldingsoplysninger')
        self.assertContains(response, 'bafimoku')

    def test_detail_hides_credentials_for_unenrolled(self):
        """School detail hides credentials for unenrolled schools."""
        self.school.enrolled_at = None
        self.school.save()
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('schools:detail', kwargs={'pk': self.school.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Tilmeldingsoplysninger')

    def test_regenerate_credentials(self):
        """Regenerate credentials creates new password and token."""
        self.client.login(username='testuser', password='testpass123')
        old_password = self.school.signup_password
        old_token = self.school.signup_token

        response = self.client.post(
            reverse('schools:regenerate-credentials', kwargs={'pk': self.school.pk})
        )
        self.assertEqual(response.status_code, 200)

        self.school.refresh_from_db()
        self.assertNotEqual(self.school.signup_password, old_password)
        self.assertNotEqual(self.school.signup_token, old_token)
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/schools/tests.py::SchoolCredentialsViewTest -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Add view to `apps/schools/views.py`:

```python
@method_decorator(staff_required, name="dispatch")
class RegenerateCredentialsView(View):
    def post(self, request, pk):
        school = get_object_or_404(School, pk=pk)
        school.generate_credentials()
        messages.success(request, f'Nye tilmeldingsoplysninger genereret for "{school.name}".')
        return JsonResponse({
            "success": True,
            "password": school.signup_password,
            "token": school.signup_token,
        })
```

Add URL to `apps/schools/urls.py`:

```python
    path('<int:pk>/regenerate-credentials/', views.RegenerateCredentialsView.as_view(), name='regenerate-credentials'),
```

Update `apps/schools/templates/schools/school_detail.html` - add credentials card after the Pladser card (around line 151):

```html
        {% if school.is_enrolled %}
        <div class="card mb-4">
            <div class="card-header">
                <i class="bi bi-key me-2"></i>Tilmeldingsoplysninger
            </div>
            <div class="card-body">
                <p class="text-muted small mb-3">Bruges til kursustilmelding</p>

                <div class="mb-3">
                    <label class="form-label fw-bold">Kode</label>
                    <div class="input-group">
                        <input type="password" class="form-control" id="signup-password"
                               value="{{ school.signup_password }}" readonly>
                        <button class="btn btn-outline-secondary" type="button"
                                onclick="togglePassword()" title="Vis/skjul">
                            <i class="bi bi-eye" id="password-toggle-icon"></i>
                        </button>
                        <button class="btn btn-outline-secondary" type="button"
                                onclick="copyToClipboard('signup-password')" title="Kopiér">
                            <i class="bi bi-clipboard"></i>
                        </button>
                    </div>
                </div>

                <div class="mb-3">
                    <label class="form-label fw-bold">Direkte link</label>
                    <div class="input-group">
                        <input type="text" class="form-control form-control-sm" id="signup-link"
                               value="{{ request.scheme }}://{{ request.get_host }}/signup/course/?token={{ school.signup_token }}"
                               readonly style="font-size: 0.8rem;">
                        <button class="btn btn-outline-secondary btn-sm" type="button"
                                onclick="copyToClipboard('signup-link')" title="Kopiér">
                            <i class="bi bi-clipboard"></i>
                        </button>
                    </div>
                </div>

                <button type="button" class="btn btn-outline-warning btn-sm"
                        hx-post="{% url 'schools:regenerate-credentials' school.pk %}"
                        hx-confirm="Er du sikker? Den gamle kode vil ikke længere virke."
                        hx-swap="none">
                    <i class="bi bi-arrow-clockwise me-1"></i>Generer ny kode
                </button>
            </div>
        </div>
        {% endif %}
```

Add JavaScript at the end of the template (or in a script block):

```html
{% block extra_js %}
<script>
function togglePassword() {
    const input = document.getElementById('signup-password');
    const icon = document.getElementById('password-toggle-icon');
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('bi-eye');
        icon.classList.add('bi-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.remove('bi-eye-slash');
        icon.classList.add('bi-eye');
    }
}

function copyToClipboard(elementId) {
    const input = document.getElementById(elementId);
    const originalType = input.type;
    input.type = 'text';
    input.select();
    document.execCommand('copy');
    input.type = originalType;

    // Show feedback
    const btn = input.nextElementSibling;
    const originalHtml = btn.innerHTML;
    btn.innerHTML = '<i class="bi bi-check"></i>';
    setTimeout(() => { btn.innerHTML = originalHtml; }, 1500);
}
</script>
{% endblock %}
```

**Step 4: Run test to verify it passes**

Run: `pytest apps/schools/tests.py::SchoolCredentialsViewTest -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/schools/views.py apps/schools/urls.py apps/schools/templates/schools/school_detail.html
git commit -m "$(cat <<'EOF'
feat(schools): add credentials section to school detail page

- Shows password (hidden by default) with reveal/copy buttons
- Shows direct signup link with copy button
- Regenerate credentials button with confirmation

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: Remove SchoolSignup Model

**Files:**
- Modify: `apps/signups/models.py`
- Modify: `apps/signups/admin.py`
- Modify: `apps/signups/tests.py`
- Create: migration to delete model

**Step 1: Update tests to remove SchoolSignup references**

In `apps/signups/tests.py`, remove imports and tests that reference `SchoolSignup`:

```python
# Remove from imports:
# from .models import SchoolSignup

# Remove entire test class if it tests SchoolSignup model directly
```

**Step 2: Update admin.py**

Remove SchoolSignup admin registration from `apps/signups/admin.py`:

```python
# Remove:
# from .models import SchoolSignup
# @admin.register(SchoolSignup)
# class SchoolSignupAdmin(...):
```

**Step 3: Update models.py**

Remove SchoolSignup model from `apps/signups/models.py`:

```python
# Remove entire SchoolSignup class
```

**Step 4: Create migration**

Run: `python manage.py makemigrations signups --name remove_schoolsignup`
Run: `python manage.py migrate`

**Step 5: Run all tests**

Run: `pytest apps/signups/tests.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add apps/signups/models.py apps/signups/admin.py apps/signups/tests.py apps/signups/migrations/
git commit -m "$(cat <<'EOF'
refactor(signups): remove SchoolSignup model

School enrollment is now instant - no need for application processing.
The SchoolSignup model and admin are removed.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: Run Full Test Suite and Final Cleanup

**Step 1: Run full test suite**

Run: `pytest -v`
Expected: All tests PASS

**Step 2: Check for linting issues**

Run: `ruff check apps/`
Fix any issues found.

**Step 3: Final commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
chore: cleanup and fix any linting issues

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Summary

This plan implements:
1. **Password generation utilities** - pronounceable passwords and tokens
2. **School model changes** - signup_password and signup_token fields
3. **UserProfile model** - notification preferences
4. **User form updates** - notification checkbox
5. **Email services** - enrollment confirmation and staff notifications
6. **School signup rewrite** - instant enrollment with credentials
7. **Password validation endpoint** - AJAX validation
8. **Course signup auth** - token, password, and staff modes
9. **Template updates** - password form and auth UI
10. **School detail credentials** - view and regenerate credentials
11. **SchoolSignup removal** - cleanup old model
12. **Final testing** - ensure everything works together
