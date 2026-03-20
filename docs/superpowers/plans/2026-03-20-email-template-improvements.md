# Email Template Improvements (OSO-207) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lock down email template types, add a coordinator signup email, expand template variables, and add coordinator confirmation UI to the course signup page.

**Architecture:** Add a `description` field and new `COORDINATOR_SIGNUP` type to the EmailTemplate model, seeded via migration. Extend context builders in services.py with new variables. Add `send_coordinator_signup_confirmation()` following the existing email sending pattern. Add coordinator confirmation section to the course signup template with JS toggle for email override.

**Tech Stack:** Django 5.x, Django admin (Summernote), Resend API, Django templates, vanilla JavaScript

**Spec:** `docs/superpowers/specs/2026-03-20-email-template-improvements-design.md`

---

### Task 1: Add `description` field and new EmailType to model

**Files:**
- Modify: `apps/emails/models.py`

- [ ] **Step 1: Add `COORDINATOR_SIGNUP` to `EmailType` and `description` field to `EmailTemplate`**

In `apps/emails/models.py`, add the new choice and field:

```python
class EmailType(models.TextChoices):
    SIGNUP_CONFIRMATION = "signup_confirmation", "Tilmeldingsbekræftelse"
    COURSE_REMINDER = "course_reminder", "Kursuspåmindelse (14 dage før)"
    SCHOOL_ENROLLMENT_CONFIRMATION = "school_enrollment_confirmation", "Skoletilmeldingsbekræftelse"
    COORDINATOR_SIGNUP = "coordinator_signup", "Koordinator-tilmeldingsbekræftelse"
```

Add `description` field to `EmailTemplate` after `is_active`:

```python
    description = models.TextField(
        blank=True,
        verbose_name="Beskrivelse",
        help_text="Beskrivelse af hvornår denne e-mail sendes og til hvem",
    )
```

- [ ] **Step 2: Create migration**

Run: `cd /home/niec/Documents/basal/basal-app && .venv/bin/python manage.py makemigrations emails -n add_description_and_coordinator_type`

Expected: Migration file created in `apps/emails/migrations/`

- [ ] **Step 3: Commit**

```bash
git add apps/emails/models.py apps/emails/migrations/0009_add_description_and_coordinator_type.py
git commit -m "feat(emails): add description field and coordinator_signup email type"
```

---

### Task 2: Data migration — seed descriptions and coordinator template

**Files:**
- Create: `apps/emails/migrations/0010_seed_coordinator_template.py` (via `makemigrations --empty`)

- [ ] **Step 1: Create empty migration**

Run: `cd /home/niec/Documents/basal/basal-app && .venv/bin/python manage.py makemigrations emails --empty -n seed_coordinator_template`

- [ ] **Step 2: Write the data migration**

Edit the generated migration file:

```python
from django.db import migrations


DESCRIPTIONS = {
    "signup_confirmation": "Sendes til hver deltager ved kursustilmelding.",
    "course_reminder": "Sendes til hver deltager 14 dage før kursusstart. Kursusmateriale vedhæftes automatisk.",
    "school_enrollment_confirmation": "Sendes til koordinator når en skole tilmelder sig Basal.",
    "coordinator_signup": "Sendes til skolens koordinator når deltagere tilmeldes et kursus. Indeholder oversigt over tilmeldte deltagere.",
}


def seed_data(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")

    # Update descriptions on existing templates
    for email_type, description in DESCRIPTIONS.items():
        EmailTemplate.objects.filter(email_type=email_type).update(description=description)

    # Create coordinator template if it doesn't exist
    EmailTemplate.objects.get_or_create(
        email_type="coordinator_signup",
        defaults={
            "subject": "Kursustilmelding – {{ school_name }}",
            "body_html": (
                "<p>Kære {{ coordinator_name }},</p>"
                "<p>Følgende deltagere fra {{ school_name }} er blevet tilmeldt kurset "
                "<strong>{{ course_title }}</strong>:</p>"
                "{{ participants_list }}"
                "<p><strong>Kursusdetaljer:</strong></p>"
                "<ul>"
                "    <li>Dato: {{ course_date }}</li>"
                "    <li>Sted: {{ course_location }}</li>"
                "</ul>"
                "<p>Med venlig hilsen,<br>Basal</p>"
            ),
            "is_active": True,
            "description": DESCRIPTIONS["coordinator_signup"],
        },
    )


def unseed_data(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    EmailTemplate.objects.filter(email_type="coordinator_signup").delete()
    EmailTemplate.objects.all().update(description="")


class Migration(migrations.Migration):
    dependencies = [
        ("emails", "0009_add_description_and_coordinator_type"),
    ]

    operations = [
        migrations.RunPython(seed_data, unseed_data),
    ]
```

- [ ] **Step 3: Run migration**

Run: `cd /home/niec/Documents/basal/basal-app && .venv/bin/python manage.py migrate emails`

Expected: Both migrations apply successfully.

- [ ] **Step 4: Commit**

```bash
git add apps/emails/migrations/0010_seed_coordinator_template.py
git commit -m "data(emails): seed coordinator template and add descriptions to all templates"
```

---

### Task 3: Lock down admin — read-only type, no add/delete

**Files:**
- Modify: `apps/emails/admin.py`
- Test: `apps/emails/tests.py`

- [ ] **Step 1: Write tests for admin lockdown**

Add to `apps/emails/tests.py`:

```python
from django.contrib.auth.models import User


class EmailTemplateAdminTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser("admin", "admin@test.com", "password")
        self.client.force_login(self.admin_user)
        # Ensure templates exist
        for et in EmailType.values:
            EmailTemplate.objects.get_or_create(
                email_type=et,
                defaults={"subject": "Test", "body_html": "<p>Test</p>", "is_active": True},
            )

    def test_admin_cannot_add_template(self):
        """Add button should not be available — returns 403."""
        response = self.client.get("/admin/emails/emailtemplate/add/")
        self.assertEqual(response.status_code, 403)

    def test_admin_cannot_delete_template(self):
        """Delete action should not be available."""
        template = EmailTemplate.objects.first()
        response = self.client.post(
            f"/admin/emails/emailtemplate/{template.pk}/delete/",
            {"post": "yes"},
        )
        self.assertEqual(response.status_code, 403)

    def test_email_type_is_readonly_on_edit(self):
        """email_type field should be read-only when editing."""
        template = EmailTemplate.objects.first()
        response = self.client.get(f"/admin/emails/emailtemplate/{template.pk}/change/")
        self.assertEqual(response.status_code, 200)
        # email_type should not be an editable field in the form
        self.assertNotContains(response, 'name="email_type"')

    def test_description_is_shown_on_edit(self):
        """description field should be visible when editing."""
        template = EmailTemplate.objects.filter(description__gt="").first()
        if template:
            response = self.client.get(f"/admin/emails/emailtemplate/{template.pk}/change/")
            self.assertContains(response, template.description)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/niec/Documents/basal/basal-app && .venv/bin/python -m pytest apps/emails/tests.py::EmailTemplateAdminTest -v`

Expected: Failures — add/delete still allowed, email_type still editable.

- [ ] **Step 3: Update admin to lock down templates**

Replace the entire `EmailTemplateAdmin` class in `apps/emails/admin.py`:

```python
@admin.register(EmailTemplate)
class EmailTemplateAdmin(SummernoteModelAdmin):
    list_display = ["email_type", "subject", "is_active", "updated_at"]
    list_filter = ["is_active", "email_type"]
    search_fields = ["subject", "body_html"]
    readonly_fields = ["email_type", "description", "updated_at", "available_variables"]
    summernote_fields = ("body_html",)

    fieldsets = (
        (None, {"fields": ("email_type", "description", "is_active")}),
        (
            "Indhold",
            {
                "fields": ("subject", "body_html"),
                "description": 'Brug variabler i teksten — se "Tilgængelige variabler" nedenfor for den fulde liste.',
            },
        ),
        (
            "Tilgængelige variabler",
            {
                "fields": ("available_variables",),
                "classes": ("collapse",),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("updated_at",),
                "classes": ("collapse",),
            },
        ),
    )

    VARIABLE_DISPLAY = {
        EmailType.SIGNUP_CONFIRMATION: [
            ("participant_name", "Deltagerens navn"),
            ("participant_email", "Deltagerens e-mail"),
            ("participant_title", "Deltagerens stilling"),
            ("school_name", "Skolens navn"),
            ("course_title", "Kursets titel"),
            ("course_date", "Kursets startdato"),
            ("course_end_date", "Kursets slutdato"),
            ("course_location", "Kursets lokation"),
            ("instructors", "Undervisere (kommasepareret)"),
            ("registration_deadline", "Tilmeldingsfrist"),
            ("spots_remaining", "Ledige pladser"),
        ],
        EmailType.COURSE_REMINDER: [
            ("participant_name", "Deltagerens navn"),
            ("participant_email", "Deltagerens e-mail"),
            ("participant_title", "Deltagerens stilling"),
            ("school_name", "Skolens navn"),
            ("course_title", "Kursets titel"),
            ("course_date", "Kursets startdato"),
            ("course_end_date", "Kursets slutdato"),
            ("course_location", "Kursets lokation"),
            ("instructors", "Undervisere (kommasepareret)"),
            ("registration_deadline", "Tilmeldingsfrist"),
            ("spots_remaining", "Ledige pladser"),
        ],
        EmailType.SCHOOL_ENROLLMENT_CONFIRMATION: [
            ("contact_name", "Kontaktpersonens navn"),
            ("school_name", "Skolens navn"),
            ("school_page_url", "Link til skolens side"),
            ("signup_url", "Link til kursustilmelding"),
            ("signup_password", "Skolens tilmeldingskode"),
            ("site_url", "Sidens URL"),
            ("school_address", "Skolens adresse"),
            ("school_municipality", "Kommune"),
            ("ean_nummer", "EAN/CVR-nummer"),
        ],
        EmailType.COORDINATOR_SIGNUP: [
            ("coordinator_name", "Koordinatorens navn"),
            ("course_title", "Kursets titel"),
            ("course_date", "Kursets startdato"),
            ("course_end_date", "Kursets slutdato"),
            ("course_location", "Kursets lokation"),
            ("school_name", "Skolens navn"),
            ("participants_list", "HTML-liste over tilmeldte deltagere"),
            ("registration_deadline", "Tilmeldingsfrist"),
            ("instructors", "Undervisere (kommasepareret)"),
        ],
    }

    def available_variables(self, obj):
        if not obj or not obj.email_type:
            return ""
        variables = self.VARIABLE_DISPLAY.get(obj.email_type, [])
        items = "".join(
            f"<li><code>{{{{ {name} }}}}</code> - {desc}</li>" for name, desc in variables
        )
        return mark_safe(f"<ul>{items}</ul>")

    available_variables.short_description = "Tilgængelige variabler"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
```

Note: The `VARIABLE_DISPLAY` dict must be defined inside the class but outside `__init__`. Update the imports at the top of the file:

```python
from django.utils.safestring import mark_safe
from .models import EmailLog, EmailTemplate, EmailType
```

The existing `format_html` import can be removed (no longer used in this file).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/niec/Documents/basal/basal-app && .venv/bin/python -m pytest apps/emails/tests.py -v`

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/emails/admin.py apps/emails/tests.py
git commit -m "feat(emails): lock down admin — read-only type/description, no add/delete"
```

---

### Task 4: Extend template variables in services.py

**Files:**
- Modify: `apps/emails/services.py`
- Test: `apps/emails/tests.py`

- [ ] **Step 1: Write tests for new context variables**

Add to `apps/emails/tests.py`:

```python
from datetime import date

from apps.courses.models import Course, CourseSignUp, Instructor, Location


class SignupContextTest(TestCase):
    def setUp(self):
        self.location = Location.objects.create(
            name="Teststed", street_address="Testvej 1", postal_code="1234", municipality="Testby"
        )
        self.instructor = Instructor.objects.create(name="Hans Hansen")
        self.course = Course.objects.create(
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 2),
            location=self.location,
            capacity=30,
            registration_deadline=date(2026, 5, 15),
        )
        self.course.instructors.add(self.instructor)
        self.school = School.objects.create(
            name="Test School", adresse="Skolevej 1", kommune="Testby"
        )
        self.signup = CourseSignUp.objects.create(
            course=self.course,
            school=self.school,
            participant_name="Test Deltager",
            participant_email="test@example.com",
            participant_title="Lærer",
        )

    def test_get_signup_context_includes_new_variables(self):
        from apps.emails.services import get_signup_context

        ctx = get_signup_context(self.signup)
        self.assertIn("registration_deadline", ctx)
        self.assertIn("course_end_date", ctx)
        self.assertIn("instructors", ctx)
        self.assertIn("spots_remaining", ctx)
        self.assertEqual(ctx["instructors"], "Hans Hansen")
        self.assertEqual(ctx["spots_remaining"], 29)  # 30 capacity - 1 signup

    def test_get_signup_context_handles_no_deadline(self):
        from apps.emails.services import get_signup_context

        self.course.registration_deadline = None
        self.course.save()
        ctx = get_signup_context(self.signup)
        self.assertEqual(ctx["registration_deadline"], "")


class SchoolEnrollmentContextTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Test School",
            adresse="Skolevej 1",
            postnummer="1234",
            by="Testby",
            kommune="Testkommune",
            ean_nummer="1234567890123",
            signup_token="abc123",
            signup_password="testpass",
        )

    def test_get_school_enrollment_context_includes_new_variables(self):
        from apps.emails.services import get_school_enrollment_context

        ctx = get_school_enrollment_context(self.school, "Test Person")
        self.assertEqual(ctx["school_address"], "Skolevej 1")
        self.assertEqual(ctx["school_municipality"], "Testkommune")
        self.assertEqual(ctx["ean_nummer"], "1234567890123")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/niec/Documents/basal/basal-app && .venv/bin/python -m pytest apps/emails/tests.py::SignupContextTest apps/emails/tests.py::SchoolEnrollmentContextTest -v`

Expected: KeyError failures — new variables don't exist yet.

- [ ] **Step 3: Extend `get_signup_context` in `services.py`**

Replace the `get_signup_context` function:

```python
def get_signup_context(signup):
    """Build template context from a CourseSignUp instance."""
    course = signup.course
    return {
        "participant_name": signup.participant_name,
        "participant_email": signup.participant_email,
        "participant_title": signup.participant_title,
        "school_name": signup.school.name,
        "course_title": course.display_name,
        "course_date": date_format(course.start_date, "j. F Y"),
        "course_end_date": date_format(course.end_date, "j. F Y"),
        "course_location": course.location.full_address if course.location else "",
        "instructors": ", ".join(course.instructors.values_list("name", flat=True)),
        "registration_deadline": date_format(course.registration_deadline, "j. F Y") if course.registration_deadline else "",
        "spots_remaining": course.spots_remaining,
    }
```

- [ ] **Step 4: Extend `get_school_enrollment_context` in `services.py`**

Replace the `get_school_enrollment_context` function:

```python
def get_school_enrollment_context(school, contact_name):
    """Build template context for school enrollment confirmation."""
    return {
        "contact_name": contact_name,
        "school_name": school.name,
        "school_page_url": f"{settings.SITE_URL}/school/{school.signup_token}/",
        "signup_url": f"{settings.SITE_URL}/signup/course/?token={school.signup_token}",
        "signup_password": school.signup_password,
        "site_url": settings.SITE_URL,
        "school_address": school.adresse,
        "school_municipality": school.kommune,
        "ean_nummer": school.ean_nummer or "",
    }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/niec/Documents/basal/basal-app && .venv/bin/python -m pytest apps/emails/tests.py -v`

Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add apps/emails/services.py apps/emails/tests.py
git commit -m "feat(emails): extend template variables for course signup and school enrollment"
```

---

### Task 5: Add coordinator email sending function

**Files:**
- Modify: `apps/emails/services.py`
- Test: `apps/emails/tests.py`

- [ ] **Step 1: Write tests for coordinator email**

Add to `apps/emails/tests.py`:

```python
from apps.schools.models import Person


class CoordinatorEmailTest(TestCase):
    def setUp(self):
        self.location = Location.objects.create(
            name="Teststed", street_address="Testvej 1", postal_code="1234", municipality="Testby"
        )
        self.course = Course.objects.create(
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 2),
            location=self.location,
            capacity=30,
        )
        self.school = School.objects.create(
            name="Test School", adresse="Skolevej 1", kommune="Testby"
        )
        self.coordinator = Person.objects.create(
            school=self.school,
            name="Koordinator Person",
            email="koordinator@example.com",
            is_koordinator=True,
        )
        self.signups = [
            CourseSignUp.objects.create(
                course=self.course,
                school=self.school,
                participant_name="Deltager 1",
                participant_email="d1@example.com",
            ),
            CourseSignUp.objects.create(
                course=self.course,
                school=self.school,
                participant_name="Deltager 2",
                participant_email="d2@example.com",
            ),
        ]
        # Ensure template exists
        EmailTemplate.objects.get_or_create(
            email_type="coordinator_signup",
            defaults={
                "subject": "Tilmelding – {{ school_name }}",
                "body_html": "<p>{{ coordinator_name }}</p>{{ participants_list }}",
                "is_active": True,
            },
        )

    @override_settings(RESEND_API_KEY=None)
    def test_sends_to_coordinator(self):
        from apps.emails.models import EmailLog
        from apps.emails.services import send_coordinator_signup_confirmation

        result = send_coordinator_signup_confirmation(self.school, self.course, self.signups)
        self.assertTrue(result)
        log = EmailLog.objects.filter(email_type="coordinator_signup").first()
        self.assertIsNotNone(log)
        self.assertEqual(log.recipient_email, "koordinator@example.com")
        self.assertEqual(log.recipient_name, "Koordinator Person")

    @override_settings(RESEND_API_KEY=None)
    def test_override_email_replaces_coordinator(self):
        from apps.emails.models import EmailLog
        from apps.emails.services import send_coordinator_signup_confirmation

        result = send_coordinator_signup_confirmation(
            self.school, self.course, self.signups, override_email="other@example.com"
        )
        self.assertTrue(result)
        log = EmailLog.objects.filter(email_type="coordinator_signup").first()
        self.assertEqual(log.recipient_email, "other@example.com")
        # recipient_name should still be the coordinator's name
        self.assertEqual(log.recipient_name, "Koordinator Person")

    @override_settings(RESEND_API_KEY=None)
    def test_skips_when_no_coordinator_and_no_override(self):
        from apps.emails.services import send_coordinator_signup_confirmation

        self.coordinator.delete()
        result = send_coordinator_signup_confirmation(self.school, self.course, self.signups)
        self.assertFalse(result)

    @override_settings(RESEND_API_KEY=None)
    def test_skips_when_coordinator_has_no_email(self):
        from apps.emails.services import send_coordinator_signup_confirmation

        self.coordinator.email = ""
        self.coordinator.save()
        result = send_coordinator_signup_confirmation(self.school, self.course, self.signups)
        self.assertFalse(result)

    @override_settings(RESEND_API_KEY=None)
    def test_context_includes_participants_list(self):
        from apps.emails.services import get_coordinator_signup_context

        ctx = get_coordinator_signup_context(self.coordinator, self.course, self.signups)
        self.assertIn("Deltager 1", ctx["participants_list"])
        self.assertIn("Deltager 2", ctx["participants_list"])
        self.assertEqual(ctx["coordinator_name"], "Koordinator Person")
        self.assertEqual(ctx["school_name"], "Test School")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/niec/Documents/basal/basal-app && .venv/bin/python -m pytest apps/emails/tests.py::CoordinatorEmailTest -v`

Expected: ImportError — functions don't exist yet.

- [ ] **Step 3: Implement `get_coordinator_signup_context` and `send_coordinator_signup_confirmation`**

Add to `apps/emails/services.py` after `send_course_reminder`:

```python
def get_coordinator_signup_context(coordinator, course, signups):
    """Build template context for coordinator signup confirmation."""
    participants_html = "<ul>" + "".join(
        f"<li>{s.participant_name} ({s.participant_email})</li>" for s in signups
    ) + "</ul>"
    return {
        "coordinator_name": coordinator.name if coordinator else "Koordinator",
        "course_title": course.display_name,
        "course_date": date_format(course.start_date, "j. F Y"),
        "course_end_date": date_format(course.end_date, "j. F Y"),
        "course_location": course.location.full_address if course.location else "",
        "school_name": signups[0].school.name if signups else "",
        "participants_list": participants_html,
        "registration_deadline": date_format(course.registration_deadline, "j. F Y") if course.registration_deadline else "",
        "instructors": ", ".join(course.instructors.values_list("name", flat=True)),
    }


def send_coordinator_signup_confirmation(school, course, signups, override_email=None):
    """
    Send signup confirmation to the school's coordinator.

    Args:
        school: School instance
        course: Course instance
        signups: list of CourseSignUp instances from this batch
        override_email: optional email to send to instead of coordinator

    Returns:
        True if successful, False otherwise
    """
    coordinator = school.people.filter(is_koordinator=True).first()

    # Determine recipient
    if override_email:
        recipient_email = override_email
        recipient_name = coordinator.name if coordinator else "Koordinator"
    elif coordinator and coordinator.email:
        recipient_email = coordinator.email
        recipient_name = coordinator.name
    else:
        logger.warning(f"No coordinator email for school {school.name} — skipping coordinator notification")
        return False

    try:
        template = EmailTemplate.objects.get(email_type=EmailType.COORDINATOR_SIGNUP, is_active=True)
    except EmailTemplate.DoesNotExist:
        logger.warning("No active template found for coordinator signup confirmation")
        return False

    context = get_coordinator_signup_context(coordinator, course, signups)
    subject = render_template(template.subject, context)
    body_html = add_email_footer(render_template(template.body_html, context))

    # Enforce email domain allowlist
    if not check_email_domain_allowed(recipient_email):
        logger.warning(
            f"[EMAIL BLOCKED] Recipient {recipient_email} not in allowed domains: "
            f"{settings.EMAIL_ALLOWED_DOMAINS}"
        )
        EmailLog.objects.create(
            email_type=EmailType.COORDINATOR_SIGNUP,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            course=course,
            success=False,
            error_message=f"[BLOCKED] Domain not in EMAIL_ALLOWED_DOMAINS: {settings.EMAIL_ALLOWED_DOMAINS}",
        )
        return False

    if not settings.RESEND_API_KEY:
        logger.info(f"[EMAIL] To: {recipient_email}")
        logger.info(f"[EMAIL] Subject: {subject}")
        logger.info(f"[EMAIL] Body: {body_html[:200]}...")
        EmailLog.objects.create(
            email_type=EmailType.COORDINATOR_SIGNUP,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            course=course,
            success=True,
            error_message="[DEV MODE - not actually sent]",
        )
        return True

    try:
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send(
            {
                "from": settings.DEFAULT_FROM_EMAIL,
                "to": [recipient_email],
                "subject": subject,
                "html": body_html,
            }
        )
        EmailLog.objects.create(
            email_type=EmailType.COORDINATOR_SIGNUP,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            course=course,
            success=True,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send coordinator signup confirmation: {e}")
        EmailLog.objects.create(
            email_type=EmailType.COORDINATOR_SIGNUP,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            course=course,
            success=False,
            error_message=str(e),
        )
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/niec/Documents/basal/basal-app && .venv/bin/python -m pytest apps/emails/tests.py -v`

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/emails/services.py apps/emails/tests.py
git commit -m "feat(emails): add coordinator signup confirmation email"
```

---

### Task 6: Add coordinator confirmation UI to course signup page

**Files:**
- Modify: `apps/signups/templates/signups/course_signup.html`

- [ ] **Step 1: Add coordinator confirmation section to the template**

In `apps/signups/templates/signups/course_signup.html`, add the following HTML **after** the `seat-info-box` and `seats-warning` divs (after line 143) and **before** the submit button div (line 145):

```html
    <div id="coordinator-confirmation" class="card mb-3" style="display: none;">
        <div class="card-body">
            <p class="mb-2">
                <i class="bi bi-envelope me-1"></i>
                Bekræftelse sendes også til koordinator: <strong id="coordinator-confirm-name"></strong>
                (<span id="coordinator-confirm-email"></span>)
            </p>
            <div class="form-check mb-2">
                <input type="checkbox" class="form-check-input" id="override-coordinator-email-check">
                <label class="form-check-label" for="override-coordinator-email-check">
                    Skal bekræftelsen sendes til en anden email?
                </label>
            </div>
            <div id="override-email-field" style="display: none;">
                <input type="email" name="coordinator_email_override" class="form-control"
                       placeholder="Indtast alternativ e-mail">
            </div>
        </div>
    </div>
```

- [ ] **Step 2: Add JavaScript to populate and toggle the section**

In the `<script>` block, add these variable declarations alongside the existing ones (after `let missingEan = false;` around line 194):

```javascript
    const coordinatorConfirmation = document.getElementById('coordinator-confirmation');
    const coordinatorConfirmName = document.getElementById('coordinator-confirm-name');
    const coordinatorConfirmEmail = document.getElementById('coordinator-confirm-email');
    const overrideCheck = document.getElementById('override-coordinator-email-check');
    const overrideField = document.getElementById('override-email-field');
```

Add the toggle listener after the variable declarations:

```javascript
    if (overrideCheck) {
        overrideCheck.addEventListener('change', function() {
            overrideField.style.display = this.checked ? 'block' : 'none';
            if (!this.checked) {
                overrideField.querySelector('input').value = '';
            }
        });
    }
```

Extend the existing `updateKoordinatorDisplay` function to also update the coordinator confirmation section. Add at the end of the `if (data && data.koordinator)` branch:

```javascript
            // Update coordinator confirmation section
            if (coordinatorConfirmation) {
                coordinatorConfirmName.textContent = k.name;
                coordinatorConfirmEmail.textContent = k.email || 'ingen e-mail';
                coordinatorConfirmation.style.display = k.email ? 'block' : 'none';
            }
```

And in the `else` branch (when no coordinator), add:

```javascript
            if (coordinatorConfirmation) {
                coordinatorConfirmation.style.display = 'none';
            }
```

- [ ] **Step 3: Verify in browser (manual)**

Run: `cd /home/niec/Documents/basal/basal-app && .venv/bin/python manage.py runserver`

Navigate to `/signup/course/`, select a school that has a coordinator. Verify:
- Coordinator confirmation card appears with name and email
- Checkbox toggles the override email input
- Section hidden when no school selected

- [ ] **Step 4: Commit**

```bash
git add apps/signups/templates/signups/course_signup.html
git commit -m "ui(signups): add coordinator confirmation section to course signup page"
```

---

### Task 7: Wire up coordinator email in the view

**Files:**
- Modify: `apps/signups/views.py`

- [ ] **Step 1: Update `CourseSignupView.post()` to call coordinator email**

In `apps/signups/views.py`, update the import at line 176 to also import the new function:

```python
            from apps.emails.services import send_coordinator_signup_confirmation, send_course_signup_notification, send_signup_confirmation
```

After the `send_course_signup_notification(school, course, created_signups)` line (line 198), add:

```python
            # Send confirmation to coordinator
            override_email = request.POST.get("coordinator_email_override", "").strip() or None
            if override_email:
                from django.core.validators import validate_email
                from django.core.exceptions import ValidationError as DjangoValidationError
                try:
                    validate_email(override_email)
                except DjangoValidationError:
                    override_email = None  # Fall back to coordinator email
            send_coordinator_signup_confirmation(school, course, created_signups, override_email=override_email)
```

- [ ] **Step 2: Commit**

```bash
git add apps/signups/views.py
git commit -m "feat(signups): send coordinator email on course signup"
```

---

### Task 8: Run full test suite and verify

- [ ] **Step 1: Run full email tests**

Run: `cd /home/niec/Documents/basal/basal-app && .venv/bin/python -m pytest apps/emails/tests.py -v`

Expected: All tests pass.

- [ ] **Step 2: Run signup tests**

Run: `cd /home/niec/Documents/basal/basal-app && .venv/bin/python -m pytest apps/signups/ -v`

Expected: All tests pass (or only pre-existing failures).

- [ ] **Step 3: Verify migrations are clean**

Run: `cd /home/niec/Documents/basal/basal-app && .venv/bin/python manage.py makemigrations --check`

Expected: "No changes detected"
