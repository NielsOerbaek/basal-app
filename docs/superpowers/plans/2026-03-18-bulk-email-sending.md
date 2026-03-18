# Bulk Email Sending Component — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `/masseudsendelse/` admin section where staff can compose, preview, and send templated bulk emails to filtered subsets of schools, with SSE progress streaming, dry-run, test-send, attachment support, and campaign history.

**Architecture:** New `apps/bulk_email/` Django app with six views (list, create, detail, preview AJAX, dry-run AJAX, SSE send), plus a protected attachment download. Template rendering uses Django's `Template`/`Context` engine with school+person variables. Sending streams via `StreamingHttpResponse` (gthread gunicorn workers required), consumed by `fetch()`+`ReadableStream` in the browser. The school filter UI is the reusable `school_filter.html` component from the `better-school-filter-7ac` branch, driven by a `SchoolFilterMixin` extracted from `SchoolListView`.

**Tech Stack:** Django 4+, Resend API (`resend.Emails.send()`), Bootstrap 5, Summernote WYSIWYG, `StreamingHttpResponse` + SSE, gunicorn gthread workers, pytest-django.

---

## Prerequisites

**The `better-school-filter-7ac` branch MUST be merged into this branch before starting Task 2.** It provides:
- `school_filter.html` component at `apps/schools/templates/schools/components/school_filter.html`
- `get_filter_summary(request)` function in `apps/schools/views.py`
- Fixed year-aware status filter logic in `SchoolListView.get_base_queryset()`

To merge:
```bash
git merge origin/better-school-filter-7ac
```

Resolve any conflicts, then continue.

---

## File Map

| File | Role |
|---|---|
| `apps/bulk_email/__init__.py` | App marker |
| `apps/bulk_email/apps.py` | `AppConfig` |
| `apps/bulk_email/models.py` | `BulkEmail`, `BulkEmailAttachment`, `BulkEmailRecipient` |
| `apps/bulk_email/services.py` | Template rendering, recipient resolution, missing-field detection, single-school send |
| `apps/bulk_email/views.py` | All six views + attachment upload/download |
| `apps/bulk_email/urls.py` | URL patterns |
| `apps/bulk_email/forms.py` | `BulkEmailForm` (Summernote body) |
| `apps/bulk_email/templates/bulk_email/bulk_email_list.html` | Campaign history table |
| `apps/bulk_email/templates/bulk_email/bulk_email_create.html` | Composer page (5 cards + JS) |
| `apps/bulk_email/templates/bulk_email/bulk_email_detail.html` | Campaign detail + recipient table |
| `apps/bulk_email/templates/bulk_email/bulk_email_preview.html` | Bare HTML for iframe preview |
| `apps/bulk_email/management/__init__.py` | Package marker |
| `apps/bulk_email/management/commands/__init__.py` | Package marker |
| `apps/bulk_email/management/commands/cleanup_orphan_attachments.py` | Delete unsent attachments |
| `apps/schools/mixins.py` | **New** `SchoolFilterMixin` extracted from `SchoolListView` |
| `apps/schools/views.py` | Modified: `SchoolListView` uses `SchoolFilterMixin` |
| `apps/audit/apps.py` | Register `BulkEmail` |
| `config/settings/base.py` | Add `apps.bulk_email` to `INSTALLED_APPS` |
| `config/urls.py` | Mount `/masseudsendelse/` |
| `apps/core/templates/core/base.html` | Add nav link |
| `Dockerfile` | gthread worker flags |
| `apps/bulk_email/tests/test_services.py` | Unit tests for services |
| `apps/bulk_email/tests/test_views.py` | Integration tests for views |

---

## Task 1: Merge better-school-filter branch

**Files:** none new, git operation only

- [ ] **Step 1: Merge**

```bash
git merge origin/better-school-filter-7ac
```

- [ ] **Step 2: Verify school_filter.html exists**

```bash
ls apps/schools/templates/schools/components/
# Expect: school_filter.html
```

- [ ] **Step 3: Verify get_filter_summary exists in views.py**

```bash
grep -n "def get_filter_summary" apps/schools/views.py
# Expect: a line number
```

- [ ] **Step 4: Run existing tests to confirm merge is clean**

```bash
.venv/bin/python -m pytest apps/schools/ apps/emails/ -x -q
```

Expected: tests pass (pre-existing failures in goals/core are known and unrelated).

- [ ] **Step 5: Commit merge**

```bash
git commit --no-edit  # or if auto-committed, skip
```

---

## Task 2: Extract SchoolFilterMixin

**Files:**
- Create: `apps/schools/mixins.py`
- Modify: `apps/schools/views.py` (SchoolListView uses the mixin)

The mixin provides two things to any view that includes a `school_filter.html`:
1. `get_school_filter_queryset()` — applies GET params to return filtered schools
2. `get_filter_context()` — returns the five context vars the component needs

- [ ] **Step 1: Write failing test**

Create `apps/schools/tests_filter_mixin.py`:

```python
from django.test import TestCase, RequestFactory
from apps.schools.models import School, SchoolYear
from apps.schools.mixins import SchoolFilterMixin


class DummyView(SchoolFilterMixin):
    def __init__(self, request):
        self.request = request


class SchoolFilterMixinContextTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        SchoolYear.objects.create(
            name="2024/25",
            start_date="2024-08-01",
            end_date="2025-07-31",
        )
        School.objects.create(
            name="Testskole",
            kommune="Aarhus",
            signup_token="tok",
            signup_password="pw",
        )

    def test_get_filter_context_has_required_keys(self):
        request = self.factory.get("/masseudsendelse/ny/")
        request.GET = request.GET.copy()
        view = DummyView(request)
        ctx = view.get_filter_context()
        for key in ("kommuner", "school_years", "filter_summary", "has_active_filters", "selected_year"):
            self.assertIn(key, ctx)

    def test_has_active_filters_false_when_no_params(self):
        request = self.factory.get("/masseudsendelse/ny/")
        view = DummyView(request)
        ctx = view.get_filter_context()
        self.assertFalse(ctx["has_active_filters"])

    def test_has_active_filters_true_when_search_set(self):
        request = self.factory.get("/masseudsendelse/ny/?search=foo")
        view = DummyView(request)
        ctx = view.get_filter_context()
        self.assertTrue(ctx["has_active_filters"])

    def test_selected_year_from_request(self):
        request = self.factory.get("/masseudsendelse/ny/?year=2024/25")
        view = DummyView(request)
        ctx = view.get_filter_context()
        self.assertEqual(ctx["selected_year"], "2024/25")

    def test_school_years_list(self):
        request = self.factory.get("/masseudsendelse/ny/")
        view = DummyView(request)
        ctx = view.get_filter_context()
        self.assertIn("2024/25", list(ctx["school_years"]))
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/python -m pytest apps/schools/tests_filter_mixin.py -v
```

Expected: `ModuleNotFoundError: No module named 'apps.schools.mixins'` — if Task 1 (merge) was skipped, you may instead see `ImportError: cannot import name 'get_filter_summary'`. Complete Task 1 first.

- [ ] **Step 3: Create apps/schools/mixins.py**

```python
from apps.schools.models import School, SchoolYear


FILTER_PARAMS = ["search", "year", "status_filter", "kommune", "unused_seats"]


class SchoolFilterMixin:
    """
    Mixin for views that include school_filter.html.

    Provides:
    - get_school_filter_queryset(): filtered School queryset from request.GET
    - get_filter_context(): context variables required by school_filter.html
    """

    def get_school_filter_queryset(self):
        """
        Return a filtered School queryset based on request.GET filter params.
        Mirrors SchoolListView.get_base_queryset() without pagination/sorting.
        """
        from django.db.models import Q

        queryset = School.objects.active().prefetch_related("people")
        search = self.request.GET.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(adresse__icontains=search)
                | Q(kommune__icontains=search)
                | Q(people__name__icontains=search)
                | Q(people__email__icontains=search)
            ).distinct()

        status_filter = self.request.GET.get("status_filter", "").strip()
        year_filter = self.request.GET.get("year", "").strip()

        if year_filter and status_filter:
            from apps.schools.school_years import get_school_year_dates

            try:
                start_date, end_date = get_school_year_dates(year_filter)
            except Exception:
                start_date = end_date = None

            if start_date:
                if status_filter == "tilmeldt_ny":
                    queryset = queryset.filter(
                        enrolled_at__isnull=False,
                        active_from__isnull=False,
                        active_from__gte=start_date,
                        active_from__lte=end_date,
                        opted_out_at__isnull=True,
                    )
                elif status_filter == "tilmeldt_fortsaetter":
                    queryset = queryset.filter(
                        enrolled_at__isnull=False,
                        active_from__isnull=False,
                        active_from__lt=start_date,
                    ).filter(Q(opted_out_at__isnull=True) | Q(opted_out_at__gt=start_date))
                elif status_filter == "frameldt":
                    queryset = queryset.filter(
                        opted_out_at__isnull=False,
                        opted_out_at__gte=start_date,
                        opted_out_at__lte=end_date,
                    )
                elif status_filter == "tilmeldt_venter":
                    queryset = queryset.filter(
                        enrolled_at__isnull=False,
                        active_from__isnull=False,
                        active_from__gt=end_date,
                        opted_out_at__isnull=True,
                    )
                elif status_filter == "ikke_tilmeldt":
                    queryset = queryset.filter(
                        Q(enrolled_at__isnull=True) | Q(active_from__isnull=True) | Q(opted_out_at__lte=start_date)
                    )
                    queryset = [s for s in queryset if s.get_status_for_year(year_filter)[0] == "ikke_tilmeldt"]
        elif year_filter:
            # Year only: schools active at any point in that year
            from apps.schools.school_years import get_school_year_dates

            try:
                start_date, end_date = get_school_year_dates(year_filter)
                queryset = queryset.filter(
                    enrolled_at__isnull=False,
                    active_from__isnull=False,
                    active_from__lte=end_date,
                ).filter(Q(opted_out_at__isnull=True) | Q(opted_out_at__gt=start_date))
            except Exception:
                pass
        elif status_filter:
            if status_filter == "tilmeldt":
                queryset = queryset.filter(enrolled_at__isnull=False, opted_out_at__isnull=True)
            elif status_filter == "tilmeldt_ny":
                from apps.schools.school_years import get_current_school_year

                current_sy = get_current_school_year()
                queryset = queryset.filter(
                    enrolled_at__isnull=False,
                    active_from__isnull=False,
                    active_from__gte=current_sy.start_date,
                    active_from__lte=current_sy.end_date,
                    opted_out_at__isnull=True,
                )
            elif status_filter == "tilmeldt_fortsaetter":
                from apps.schools.school_years import get_current_school_year

                current_sy = get_current_school_year()
                queryset = queryset.filter(
                    enrolled_at__isnull=False,
                    active_from__isnull=False,
                    active_from__lt=current_sy.start_date,
                    opted_out_at__isnull=True,
                )
            elif status_filter == "tilmeldt_venter":
                from apps.schools.school_years import get_current_school_year

                current_sy = get_current_school_year()
                queryset = queryset.filter(
                    enrolled_at__isnull=False,
                    active_from__isnull=False,
                    active_from__gt=current_sy.end_date,
                    opted_out_at__isnull=True,
                )
            elif status_filter == "ikke_tilmeldt":
                queryset = queryset.filter(enrolled_at__isnull=True)
            elif status_filter == "frameldt":
                queryset = queryset.filter(opted_out_at__isnull=False)
            elif status_filter == "har_tilmeldinger_ikke_basal":
                from apps.courses.models import CourseSignUp
                from django.db.models import Q

                schools_with_signups = (
                    CourseSignUp.objects.filter(school__isnull=False).values_list("school_id", flat=True).distinct()
                )
                queryset = queryset.filter(pk__in=schools_with_signups).filter(
                    Q(enrolled_at__isnull=True) | Q(opted_out_at__isnull=False)
                )

        kommune_filter = self.request.GET.get("kommune", "").strip()
        if kommune_filter:
            queryset = queryset.filter(kommune=kommune_filter)

        unused_filter = self.request.GET.get("unused_seats", "").strip()
        if unused_filter in ("yes", "no"):
            if not isinstance(queryset, list):
                queryset = list(queryset)
            if unused_filter == "yes":
                queryset = [s for s in queryset if s.remaining_seats > 0]
            else:
                queryset = [s for s in queryset if s.remaining_seats == 0]

        return queryset

    def get_filter_context(self):
        """Return context variables required by school_filter.html."""
        from apps.schools.views import get_filter_summary

        kommuner = (
            School.objects.active()
            .exclude(kommune="")
            .values_list("kommune", flat=True)
            .distinct()
            .order_by("kommune")
        )
        school_years = SchoolYear.objects.all().order_by("start_date").values_list("name", flat=True)
        has_active_filters = any(self.request.GET.get(p) for p in FILTER_PARAMS)
        return {
            "kommuner": list(kommuner),
            "school_years": list(school_years),
            "filter_summary": get_filter_summary(self.request),
            "has_active_filters": has_active_filters,
            "selected_year": self.request.GET.get("year", "").strip() or None,
        }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest apps/schools/tests_filter_mixin.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Update SchoolListView to use the mixin**

In `apps/schools/views.py`, add import and update `SchoolListView`:

```python
# Add to imports at top of file:
from apps.schools.mixins import SchoolFilterMixin

# Change class definition from:
class SchoolListView(SortableMixin, ListView):
# To:
class SchoolListView(SchoolFilterMixin, SortableMixin, ListView):
```

Then in `SchoolListView.get_context_data()`, replace the inline `kommuner` and `school_years` context building with the mixin:

```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context.update(self.get_filter_context())
    # ... rest of existing context (filtered_count, enrolled_count, etc.)
```

- [ ] **Step 6: Verify SchoolListView still works**

```bash
.venv/bin/python -m pytest apps/schools/ -x -q
```

Expected: passes (same as before).

- [ ] **Step 7: Commit**

```bash
git add apps/schools/mixins.py apps/schools/views.py apps/schools/tests_filter_mixin.py
git commit -m "refactor: extract SchoolFilterMixin from SchoolListView for reuse"
```

---

## Task 3: App Scaffold

**Files:**
- Create: `apps/bulk_email/__init__.py`, `apps/bulk_email/apps.py`, `apps/bulk_email/urls.py`
- Modify: `config/settings/base.py`, `config/urls.py`, `apps/core/templates/core/base.html`

- [ ] **Step 1: Create app files**

`apps/bulk_email/__init__.py` — empty file.

`apps/bulk_email/apps.py`:
```python
from django.apps import AppConfig


class BulkEmailConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.bulk_email"
    verbose_name = "Masseudsendelse"
```

`apps/bulk_email/urls.py`:
```python
from django.urls import path
from . import views

app_name = "bulk_email"

urlpatterns = [
    path("", views.BulkEmailListView.as_view(), name="list"),
    path("ny/", views.BulkEmailCreateView.as_view(), name="create"),
    path("ny/upload/", views.BulkEmailAttachmentUploadView.as_view(), name="attachment_upload"),
    path("<int:pk>/", views.BulkEmailDetailView.as_view(), name="detail"),
    path("preview/", views.BulkEmailPreviewView.as_view(), name="preview"),
    path("dry-run/", views.BulkEmailDryRunView.as_view(), name="dry_run"),
    path("send/", views.BulkEmailSendView.as_view(), name="send"),
    path("attachments/<int:pk>/", views.BulkEmailAttachmentDownloadView.as_view(), name="attachment_download"),
]
```

- [ ] **Step 2: Register app in settings**

In `config/settings/base.py`, add `"apps.bulk_email"` to `INSTALLED_APPS` after `"apps.goals"`:

```python
INSTALLED_APPS = [
    # ... existing entries ...
    "apps.goals",
    "apps.bulk_email",  # add this
]
```

- [ ] **Step 3: Mount URLs**

In `config/urls.py`, add:

```python
path("masseudsendelse/", include("apps.bulk_email.urls")),
```

Place it alongside the other app includes (after `projektmaal/`).

- [ ] **Step 4: Add nav link**

In `apps/core/templates/core/base.html`, add a nav item alongside "Henvendelser":

```html
<li class="nav-item">
    <a class="nav-link {% if request.resolver_match.app_name == 'bulk_email' %}active{% endif %}"
       href="{% url 'bulk_email:list' %}">
        Masseudsendelse
    </a>
</li>
```

- [ ] **Step 5: Create placeholder views so URLs resolve**

Create `apps/bulk_email/views.py` with stubs (will be filled in later tasks):

```python
from django.views import View
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from apps.core.decorators import staff_required


@method_decorator(staff_required, name="dispatch")
class BulkEmailListView(View):
    def get(self, request):
        return HttpResponse("list placeholder")


@method_decorator(staff_required, name="dispatch")
class BulkEmailCreateView(View):
    def get(self, request):
        return HttpResponse("create placeholder")


@method_decorator(staff_required, name="dispatch")
class BulkEmailDetailView(View):
    def get(self, request, pk):
        return HttpResponse("detail placeholder")


@method_decorator(staff_required, name="dispatch")
class BulkEmailPreviewView(View):
    def post(self, request):
        return HttpResponse("preview placeholder")


@method_decorator(staff_required, name="dispatch")
class BulkEmailDryRunView(View):
    def post(self, request):
        return HttpResponse("dry-run placeholder")


@method_decorator(staff_required, name="dispatch")
class BulkEmailSendView(View):
    def post(self, request):
        return HttpResponse("send placeholder")


@method_decorator(staff_required, name="dispatch")
class BulkEmailAttachmentUploadView(View):
    def post(self, request):
        return HttpResponse("upload placeholder")


@method_decorator(staff_required, name="dispatch")
class BulkEmailAttachmentDownloadView(View):
    def get(self, request, pk):
        return HttpResponse("download placeholder")
```

- [ ] **Step 6: Verify server starts and URLs resolve**

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py show_urls 2>/dev/null | grep masseudsendelse || echo "URLs registered"
```

- [ ] **Step 7: Commit**

```bash
git add apps/bulk_email/ config/settings/base.py config/urls.py apps/core/templates/core/base.html
git commit -m "feat: scaffold bulk_email app with placeholder views and nav link"
```

---

## Task 4: Models and Migration

**Files:**
- Create: `apps/bulk_email/models.py`
- Run: migration

- [ ] **Step 1: Write models**

`apps/bulk_email/models.py`:

```python
from django.contrib.auth import get_user_model
from django.db import models

from apps.schools.models import Person, School

User = get_user_model()


class BulkEmail(models.Model):
    KOORDINATOR = "koordinator"
    OEKONOMISK_ANSVARLIG = "oekonomisk_ansvarlig"
    RECIPIENT_TYPE_CHOICES = [
        (KOORDINATOR, "Koordinator"),
        (OEKONOMISK_ANSVARLIG, "Økonomiansvarlig"),
    ]

    subject = models.CharField(max_length=500)
    body_html = models.TextField()
    recipient_type = models.CharField(max_length=30, choices=RECIPIENT_TYPE_CHOICES)
    filter_params = models.JSONField(default=dict)
    sent_at = models.DateTimeField(null=True, blank=True)
    sent_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Masseudsendelse"
        verbose_name_plural = "Masseudsendelser"

    def __str__(self):
        return f"{self.subject} ({self.sent_at or 'ikke sendt'})"

    @property
    def is_sent(self):
        return self.sent_at is not None

    @property
    def is_interrupted(self):
        """True if sending started but sent_at was never set."""
        return self.sent_at is None and self.recipients.exists()

    def get_filter_summary_display(self):
        """Return a human-readable summary of stored filter_params."""
        from apps.schools.views import get_filter_summary
        from django.http import QueryDict

        qs = QueryDict(mutable=True)
        qs.update(self.filter_params)

        class _FakeRequest:
            GET = qs

        return get_filter_summary(_FakeRequest())


class BulkEmailAttachment(models.Model):
    bulk_email = models.ForeignKey(BulkEmail, null=True, blank=True, on_delete=models.SET_NULL, related_name="attachments")
    file = models.FileField(upload_to="bulk_email_attachments/")
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at"]

    def __str__(self):
        return self.filename


class BulkEmailRecipient(models.Model):
    bulk_email = models.ForeignKey(BulkEmail, on_delete=models.CASCADE, related_name="recipients")
    person = models.ForeignKey(Person, null=True, on_delete=models.SET_NULL)
    school = models.ForeignKey(School, null=True, on_delete=models.SET_NULL)
    email = models.CharField(max_length=254)
    success = models.BooleanField(default=False)
    error_message = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["school__name"]

    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.email}"
```

- [ ] **Step 2: Create and run migration**

```bash
.venv/bin/python manage.py makemigrations bulk_email
.venv/bin/python manage.py migrate
```

- [ ] **Step 3: Write model tests**

Create `apps/bulk_email/tests/__init__.py` (empty) and `apps/bulk_email/tests/test_models.py`:

```python
from django.test import TestCase
from apps.bulk_email.models import BulkEmail, BulkEmailAttachment, BulkEmailRecipient
from apps.schools.models import School


class BulkEmailModelTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="Testskole", signup_token="tok", signup_password="pw")
        self.campaign = BulkEmail.objects.create(
            subject="Test emne",
            body_html="<p>Hej {{ skole_navn }}</p>",
            recipient_type=BulkEmail.KOORDINATOR,
            filter_params={"kommune": "Aarhus"},
        )

    def test_is_sent_false_before_send(self):
        self.assertFalse(self.campaign.is_sent)

    def test_is_interrupted_false_with_no_recipients(self):
        self.assertFalse(self.campaign.is_interrupted)

    def test_is_interrupted_true_with_recipients_and_no_sent_at(self):
        BulkEmailRecipient.objects.create(
            bulk_email=self.campaign,
            school=self.school,
            email="test@test.dk",
            success=True,
        )
        self.assertTrue(self.campaign.is_interrupted)
```

- [ ] **Step 4: Run tests**

```bash
.venv/bin/python -m pytest apps/bulk_email/tests/test_models.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/bulk_email/models.py apps/bulk_email/migrations/ apps/bulk_email/tests/
git commit -m "feat: add BulkEmail, BulkEmailAttachment, BulkEmailRecipient models"
```

---

## Task 5: Audit Registration

**Files:**
- Modify: `apps/audit/apps.py`

- [ ] **Step 1: Register BulkEmail in audit**

In `apps/audit/apps.py`, inside the `AuditConfig.ready()` method, add after the existing registrations:

```python
from apps.bulk_email.models import BulkEmail
register_for_audit(BulkEmail, AuditCfg(
    excluded_fields=["id", "created_at", "updated_at", "body_html"],
))
```

- [ ] **Step 2: Verify server still starts**

```bash
.venv/bin/python manage.py check
```

- [ ] **Step 3: Commit**

```bash
git add apps/audit/apps.py
git commit -m "feat: register BulkEmail in audit log"
```

---

## Task 6: Bulk Email Services

**Files:**
- Create: `apps/bulk_email/services.py`
- Create: `apps/bulk_email/tests/test_services.py`

Services handle template context building, recipient resolution, missing-field detection, and single-school email sending. These are pure functions — easy to test independently.

- [ ] **Step 1: Write failing tests**

`apps/bulk_email/tests/test_services.py`:

```python
import re
from django.test import TestCase, override_settings
from apps.bulk_email.models import BulkEmail, BulkEmailRecipient
from apps.bulk_email.services import (
    build_template_context,
    find_missing_variables,
    resolve_recipients,
    send_to_school,
)
from apps.schools.models import School, Person


class BuildTemplateContextTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Testskole A/S",
            adresse="Testvej 1",
            postnummer="8000",
            by="Aarhus",
            kommune="Aarhus",
            ean_nummer="1234567890123",
            enrolled_at="2024-08-01",
            active_from="2024-08-01",
            signup_token="abc123",
            signup_password="hemlig",
        )
        self.person = Person.objects.create(
            school=self.school,
            name="Kontakt Person",
            email="kontakt@testskole.dk",
            phone="11223344",
        )

    def test_school_name_mapped(self):
        ctx = build_template_context(self.school, self.person)
        self.assertEqual(ctx["skole_navn"], "Testskole A/S")

    def test_person_fields_mapped(self):
        ctx = build_template_context(self.school, self.person)
        self.assertEqual(ctx["kontakt_navn"], "Kontakt Person")
        self.assertEqual(ctx["kontakt_email"], "kontakt@testskole.dk")
        self.assertEqual(ctx["kontakt_telefon"], "11223344")

    def test_tilmeldings_link_contains_token(self):
        ctx = build_template_context(self.school, self.person)
        self.assertIn("abc123", ctx["tilmeldings_link"])

    def test_adgangskode_set(self):
        ctx = build_template_context(self.school, self.person)
        self.assertEqual(ctx["tilmeldings_adgangskode"], "hemlig")


class FindMissingVariablesTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Skole",
            signup_token="tok",
            signup_password="pw",
        )
        self.person = Person.objects.create(
            school=self.school,
            name="Person",
            email="p@s.dk",
        )

    def test_no_warnings_when_all_present(self):
        template_str = "Kære {{ kontakt_navn }}, {{ skole_navn }}"
        warnings = find_missing_variables(template_str, [(self.school, self.person)])
        self.assertEqual(warnings, [])

    def test_warning_when_ean_missing(self):
        # school has no ean_nummer
        template_str = "EAN: {{ ean_nummer }}"
        warnings = find_missing_variables(template_str, [(self.school, self.person)])
        self.assertEqual(len(warnings), 1)
        self.assertIn("ean_nummer", warnings[0]["variable"])
        self.assertIn("Skole", warnings[0]["schools"])


class ResolveRecipientsTest(TestCase):
    def setUp(self):
        self.school_with_coord = School.objects.create(
            name="Med Koordinator", signup_token="t1", signup_password="p1"
        )
        Person.objects.create(
            school=self.school_with_coord,
            name="Koordinator",
            email="k@test.dk",
            is_koordinator=True,
        )
        self.school_without_coord = School.objects.create(
            name="Uden Koordinator", signup_token="t2", signup_password="p2"
        )

    def test_returns_only_schools_with_matching_contact(self):
        schools = School.objects.filter(pk__in=[self.school_with_coord.pk, self.school_without_coord.pk])
        recipients = resolve_recipients(schools, BulkEmail.KOORDINATOR)
        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0][0], self.school_with_coord)

    def test_skipped_count_correct(self):
        schools = School.objects.filter(pk__in=[self.school_with_coord.pk, self.school_without_coord.pk])
        recipients = resolve_recipients(schools, BulkEmail.KOORDINATOR)
        # We can derive skipped count from difference
        self.assertEqual(len(recipients), 1)


@override_settings(RESEND_API_KEY=None)
class SendToSchoolTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Skole",
            signup_token="tok",
            signup_password="pw",
        )
        self.person = Person.objects.create(
            school=self.school,
            name="Person",
            email="person@test.dk",
            is_koordinator=True,
        )
        self.campaign = BulkEmail.objects.create(
            subject="Test {{ skole_navn }}",
            body_html="<p>Hej {{ kontakt_navn }}</p>",
            recipient_type=BulkEmail.KOORDINATOR,
        )

    def test_dev_mode_creates_recipient_with_success(self):
        recipient = send_to_school(self.campaign, self.school, self.person)
        self.assertIsInstance(recipient, BulkEmailRecipient)
        self.assertTrue(recipient.success)
        self.assertIn("DEV MODE", recipient.error_message)

    def test_dev_mode_snapshots_email(self):
        recipient = send_to_school(self.campaign, self.school, self.person)
        self.assertEqual(recipient.email, "person@test.dk")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest apps/bulk_email/tests/test_services.py -v
```

Expected: `ImportError: cannot import name 'build_template_context' from 'apps.bulk_email.services'`

- [ ] **Step 3: Implement services**

`apps/bulk_email/services.py`:

```python
import json
import logging
import re

import resend
from django.conf import settings
from django.template import Context, Template
from django.utils.formats import date_format

from apps.bulk_email.models import BulkEmail, BulkEmailRecipient
from apps.emails.services import EMAIL_FOOTER, check_email_domain_allowed

logger = logging.getLogger(__name__)

# All template variables and their source accessors
VARIABLE_ACCESSORS = {
    "skole_navn": lambda s, p: s.name,
    "adresse": lambda s, p: s.adresse,
    "postnummer": lambda s, p: s.postnummer,
    "by": lambda s, p: s.by,
    "kommune": lambda s, p: s.kommune,
    "ean_nummer": lambda s, p: s.ean_nummer,
    "fakturering_ean_nummer": lambda s, p: s.fakturering_ean_nummer,
    "fakturering_kontakt_navn": lambda s, p: s.fakturering_kontakt_navn,
    "fakturering_kontakt_email": lambda s, p: s.fakturering_kontakt_email,
    "tilmeldt_dato": lambda s, p: date_format(s.enrolled_at, "j. F Y") if s.enrolled_at else "",
    "aktiv_fra": lambda s, p: date_format(s.active_from, "j. F Y") if s.active_from else "",
    "kontakt_navn": lambda s, p: p.name if p else "",
    "kontakt_email": lambda s, p: p.email if p else "",
    "kontakt_telefon": lambda s, p: p.phone if p else "",
    "tilmeldings_link": lambda s, p: f"{settings.SITE_URL}/signup/course/?token={s.signup_token}" if s.signup_token else "",
    "skoleside_link": lambda s, p: f"{settings.SITE_URL}/school/{s.signup_token}/" if s.signup_token else "",
    "tilmeldings_adgangskode": lambda s, p: s.signup_password,
}

VARIABLE_NAMES = list(VARIABLE_ACCESSORS.keys())


def build_template_context(school, person):
    """Build the template rendering context dict for one school+person pair."""
    return {var: (accessor(school, person) or "") for var, accessor in VARIABLE_ACCESSORS.items()}


def render_for_school(template_str, school, person):
    """Render a template string with school+person context."""
    ctx = build_template_context(school, person)
    return Template(template_str).render(Context(ctx))


def extract_variables_from_template(template_str):
    """Return list of variable names referenced in a template string."""
    # Match {{ var_name }} — ignore block tags
    return re.findall(r"\{\{\s*(\w+)\s*\}\}", template_str)


def find_missing_variables(template_str, school_person_pairs):
    """
    For each variable referenced in template_str, find schools where it resolves to blank.

    Args:
        template_str: The subject or body template string
        school_person_pairs: list of (school, person) tuples

    Returns:
        List of dicts: [{"variable": "{{ ean_nummer }}", "schools": ["Skole A", "Skole B"]}]
    """
    referenced = extract_variables_from_template(template_str)
    warnings = []
    for var in referenced:
        if var not in VARIABLE_ACCESSORS:
            continue
        accessor = VARIABLE_ACCESSORS[var]
        missing_schools = []
        for school, person in school_person_pairs:
            value = accessor(school, person)
            if not value:
                missing_schools.append(school.name)
        if missing_schools:
            warnings.append({"variable": f"{{{{ {var} }}}}", "schools": missing_schools})
    return warnings


def resolve_recipients(schools, recipient_type):
    """
    For each school in the queryset/list, find the matching contact person.

    Args:
        schools: queryset or list of School instances (already prefetch_related("people"))
        recipient_type: BulkEmail.KOORDINATOR or BulkEmail.OEKONOMISK_ANSVARLIG

    Returns:
        List of (school, person) tuples — schools with no matching contact are omitted.
    """
    result = []
    for school in schools:
        person = None
        if recipient_type == BulkEmail.KOORDINATOR:
            person = next((p for p in school.people.all() if p.is_koordinator and p.email), None)
        elif recipient_type == BulkEmail.OEKONOMISK_ANSVARLIG:
            person = next((p for p in school.people.all() if p.is_oekonomisk_ansvarlig and p.email), None)
        if person:
            result.append((school, person))
    return result


def send_to_school(bulk_email, school, person):
    """
    Send a single bulk email to one school/person. Writes and returns a BulkEmailRecipient.
    Does NOT abort on failure — caller should continue iterating.
    """
    email_address = person.email
    subject = render_for_school(bulk_email.subject, school, person)
    body_html = render_for_school(bulk_email.body_html, school, person) + EMAIL_FOOTER

    recipient = BulkEmailRecipient(
        bulk_email=bulk_email,
        person=person,
        school=school,
        email=email_address,
    )

    # Domain allowlist check
    if not check_email_domain_allowed(email_address):
        recipient.success = False
        recipient.error_message = f"[BLOCKED] Domain not in EMAIL_ALLOWED_DOMAINS"
        recipient.save()
        return recipient

    # Dev mode guard
    if not getattr(settings, "RESEND_API_KEY", None):
        logger.info(f"[BULK EMAIL] DEV MODE — To: {email_address} Subject: {subject}")
        recipient.success = True
        recipient.error_message = "[DEV MODE - not actually sent]"
        recipient.save()
        return recipient

    try:
        resend.api_key = settings.RESEND_API_KEY
        attachments = []
        for attachment in bulk_email.attachments.all():
            with attachment.file.open("rb") as f:
                attachments.append({"filename": attachment.filename, "content": list(f.read())})

        params = {
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": [email_address],
            "subject": subject,
            "html": body_html,
        }
        if attachments:
            params["attachments"] = attachments

        resend.Emails.send(params)
        recipient.success = True
    except Exception as e:
        logger.error(f"[BULK EMAIL] Failed to send to {email_address}: {e}")
        recipient.success = False
        recipient.error_message = str(e)[:500]

    recipient.save()
    return recipient
```

- [ ] **Step 4: Run tests**

```bash
.venv/bin/python -m pytest apps/bulk_email/tests/test_services.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/bulk_email/services.py apps/bulk_email/tests/test_services.py
git commit -m "feat: add bulk_email services (template context, recipient resolution, single send)"
```

---

## Task 7: History List View and Detail View

**Files:**
- Modify: `apps/bulk_email/views.py`
- Create: `apps/bulk_email/templates/bulk_email/bulk_email_list.html`
- Create: `apps/bulk_email/templates/bulk_email/bulk_email_detail.html`
- Create: `apps/bulk_email/tests/test_views.py`

- [ ] **Step 1: Write failing tests**

`apps/bulk_email/tests/test_views.py`:

```python
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.bulk_email.models import BulkEmail, BulkEmailRecipient
from apps.schools.models import School, Person
import json

User = get_user_model()


def make_staff(username="staff"):
    return User.objects.create_user(username=username, password="pw", is_staff=True)


class BulkEmailListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_staff()
        self.client.login(username="staff", password="pw")
        self.campaign = BulkEmail.objects.create(
            subject="Test",
            body_html="<p>x</p>",
            recipient_type=BulkEmail.KOORDINATOR,
        )

    def test_list_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("bulk_email:list"))
        self.assertNotEqual(response.status_code, 200)

    def test_list_returns_200_for_staff(self):
        response = self.client.get(reverse("bulk_email:list"))
        self.assertEqual(response.status_code, 200)

    def test_list_shows_campaign(self):
        response = self.client.get(reverse("bulk_email:list"))
        self.assertContains(response, "Test")

    def test_interrupted_campaign_appears_before_sent(self):
        from django.utils import timezone
        sent = BulkEmail.objects.create(
            subject="Sent", body_html="", recipient_type=BulkEmail.KOORDINATOR, sent_at=timezone.now()
        )
        interrupted = BulkEmail.objects.create(
            subject="Afbrudt", body_html="", recipient_type=BulkEmail.KOORDINATOR
        )
        from apps.schools.models import School
        s = School.objects.create(name="S", signup_token="t", signup_password="p")
        BulkEmailRecipient.objects.create(bulk_email=interrupted, school=s, email="x@x.dk", success=True)
        response = self.client.get(reverse("bulk_email:list"))
        content = response.content.decode()
        self.assertLess(content.index("Afbrudt"), content.index("Sent"))


class BulkEmailDetailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_staff()
        self.client.login(username="staff", password="pw")
        self.school = School.objects.create(name="Skole", signup_token="tok", signup_password="pw")
        self.person = Person.objects.create(school=self.school, name="P", email="p@s.dk")
        from django.utils import timezone
        self.campaign = BulkEmail.objects.create(
            subject="Detaljetest",
            body_html="<p>x</p>",
            recipient_type=BulkEmail.KOORDINATOR,
            sent_at=timezone.now(),
        )
        BulkEmailRecipient.objects.create(
            bulk_email=self.campaign,
            school=self.school,
            person=self.person,
            email="p@s.dk",
            success=True,
        )

    def test_detail_returns_200(self):
        response = self.client.get(reverse("bulk_email:detail", args=[self.campaign.pk]))
        self.assertEqual(response.status_code, 200)

    def test_detail_shows_recipient(self):
        response = self.client.get(reverse("bulk_email:detail", args=[self.campaign.pk]))
        self.assertContains(response, "Skole")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest apps/bulk_email/tests/test_views.py::BulkEmailListViewTest -v
```

Expected: FAIL (placeholder returns 200 but no template / campaign not shown).

- [ ] **Step 3: Implement list and detail views**

Replace stubs in `apps/bulk_email/views.py`:

```python
import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import DetailView, ListView

from apps.core.decorators import staff_required
from apps.bulk_email.models import BulkEmail, BulkEmailAttachment, BulkEmailRecipient
from apps.bulk_email.services import (
    build_template_context,
    extract_variables_from_template,
    find_missing_variables,
    render_for_school,
    resolve_recipients,
    send_to_school,
    VARIABLE_NAMES,
)
from apps.schools.mixins import SchoolFilterMixin, FILTER_PARAMS

logger = logging.getLogger(__name__)


@method_decorator(staff_required, name="dispatch")
class BulkEmailListView(ListView):
    model = BulkEmail
    template_name = "bulk_email/bulk_email_list.html"
    context_object_name = "campaigns"

    def get_queryset(self):
        from django.db.models import F
        return BulkEmail.objects.prefetch_related("recipients").order_by(
            # Interrupted (sent_at=NULL) first — NULLs last with ASC, so use nulls_first
            F("sent_at").asc(nulls_first=True),
            "-created_at",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for campaign in context["campaigns"]:
            campaign._recipient_count = campaign.recipients.count()
            campaign._failure_count = campaign.recipients.filter(success=False).count()
        return context


@method_decorator(staff_required, name="dispatch")
class BulkEmailDetailView(DetailView):
    model = BulkEmail
    template_name = "bulk_email/bulk_email_detail.html"
    context_object_name = "campaign"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        campaign = self.object
        context["recipients"] = campaign.recipients.select_related("school", "person").order_by(
            "success", "school__name"
        )
        context["sent_count"] = campaign.recipients.filter(success=True).count()
        context["failed_count"] = campaign.recipients.filter(success=False).count()
        context["filter_summary"] = campaign.get_filter_summary_display()
        return context
```

- [ ] **Step 4: Create list template**

`apps/bulk_email/templates/bulk_email/bulk_email_list.html`:

```html
{% extends "core/base.html" %}

{% block title %}Masseudsendelse{% endblock %}

{% block content %}
<div class="container-fluid py-3">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h1 class="h3 mb-0">Masseudsendelse</h1>
        <a href="{% url 'bulk_email:create' %}" class="btn btn-primary">
            + Ny udsendelse
        </a>
    </div>

    {% if campaigns %}
    <div class="card">
        <div class="table-responsive">
            <table class="table table-hover mb-0">
                <thead class="table-light">
                    <tr>
                        <th>Emne</th>
                        <th>Modtagertype</th>
                        <th>Filter</th>
                        <th>Sendt</th>
                        <th>Af</th>
                        <th>Modtagere</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    {% for campaign in campaigns %}
                    <tr>
                        <td>
                            <a href="{% url 'bulk_email:detail' campaign.pk %}">
                                {{ campaign.subject|truncatechars:60 }}
                            </a>
                            {% if campaign.is_interrupted %}
                                <span class="badge bg-warning text-dark ms-1">Afbrudt</span>
                            {% endif %}
                        </td>
                        <td>{{ campaign.get_recipient_type_display }}</td>
                        <td class="text-muted small">{{ campaign.get_filter_summary_display|default:"—" }}</td>
                        <td>
                            {% if campaign.sent_at %}
                                {{ campaign.sent_at|date:"d/m/Y H:i" }}
                            {% else %}
                                <span class="text-muted">—</span>
                            {% endif %}
                        </td>
                        <td>{{ campaign.sent_by|default:"—" }}</td>
                        <td>
                            {{ campaign._recipient_count }}
                            {% if campaign._failure_count %}
                                <span class="text-danger">({{ campaign._failure_count }} fejl)</span>
                            {% endif %}
                        </td>
                        <td>
                            <a href="{% url 'bulk_email:create' %}?copy_from={{ campaign.pk }}&subject={{ campaign.subject|urlencode }}&recipient_type={{ campaign.recipient_type }}{% for k, v in campaign.filter_params.items %}&{{ k }}={{ v|urlencode }}{% endfor %}"
                               class="btn btn-sm btn-outline-secondary">
                                Kopier til ny
                            </a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    {% else %}
    <p class="text-muted">Ingen udsendelser endnu.</p>
    {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 5: Create detail template**

`apps/bulk_email/templates/bulk_email/bulk_email_detail.html`:

```html
{% extends "core/base.html" %}

{% block title %}{{ campaign.subject }}{% endblock %}

{% block content %}
<div class="container-fluid py-3">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h1 class="h3 mb-0">{{ campaign.subject|truncatechars:60 }}</h1>
        <a href="{% url 'bulk_email:create' %}?copy_from={{ campaign.pk }}&subject={{ campaign.subject|urlencode }}&recipient_type={{ campaign.recipient_type }}{% for k, v in campaign.filter_params.items %}&{{ k }}={{ v|urlencode }}{% endfor %}"
           class="btn btn-outline-secondary">
            Kopier til ny
        </a>
    </div>

    <div class="row mb-4">
        <div class="col-md-6">
            <dl class="row">
                <dt class="col-5">Modtagertype</dt>
                <dd class="col-7">{{ campaign.get_recipient_type_display }}</dd>
                <dt class="col-5">Filter</dt>
                <dd class="col-7">{{ filter_summary|default:"Ingen filtre" }}</dd>
                <dt class="col-5">Sendt</dt>
                <dd class="col-7">
                    {% if campaign.sent_at %}{{ campaign.sent_at|date:"d/m/Y H:i" }}{% else %}—{% endif %}
                </dd>
                <dt class="col-5">Sendt af</dt>
                <dd class="col-7">{{ campaign.sent_by|default:"—" }}</dd>
            </dl>
        </div>
        <div class="col-md-6">
            <div class="row text-center">
                <div class="col">
                    <div class="fs-3 fw-bold text-success">{{ sent_count }}</div>
                    <div class="text-muted small">Sendt</div>
                </div>
                <div class="col">
                    <div class="fs-3 fw-bold text-danger">{{ failed_count }}</div>
                    <div class="text-muted small">Fejlede</div>
                </div>
            </div>
        </div>
    </div>

    <div class="card">
        <div class="card-header">Modtagere ({{ recipients|length }})</div>
        <div class="table-responsive">
            <table class="table table-sm mb-0">
                <thead class="table-light">
                    <tr>
                        <th>Skole</th>
                        <th>Kontakt</th>
                        <th>E-mail</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% for r in recipients %}
                    <tr {% if not r.success %}class="table-danger"{% endif %}>
                        <td>{{ r.school.name|default:"—" }}</td>
                        <td>{{ r.person.name|default:"—" }}</td>
                        <td>{{ r.email }}</td>
                        <td>
                            {% if r.success %}
                                <span class="text-success">✓</span>
                            {% else %}
                                <span class="text-danger">✗ {{ r.error_message }}</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 6: Run tests**

```bash
.venv/bin/python -m pytest apps/bulk_email/tests/test_views.py::BulkEmailListViewTest apps/bulk_email/tests/test_views.py::BulkEmailDetailViewTest -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/bulk_email/views.py apps/bulk_email/templates/ apps/bulk_email/tests/test_views.py
git commit -m "feat: add campaign list and detail views with templates"
```

---

## Task 8: Attachment Upload and Protected Download

**Files:**
- Modify: `apps/bulk_email/views.py`
- Modify: `apps/bulk_email/tests/test_views.py`

- [ ] **Step 1: Write failing tests**

Add to `apps/bulk_email/tests/test_views.py`:

```python
import io
from django.core.files.uploadedfile import SimpleUploadedFile


class AttachmentUploadTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_staff("staff2")
        self.client.login(username="staff2", password="pw")

    def test_upload_returns_pk(self):
        f = SimpleUploadedFile("test.pdf", b"PDF content", content_type="application/pdf")
        response = self.client.post(
            reverse("bulk_email:attachment_upload"),
            {"file": f},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("pk", data)
        self.assertEqual(data["filename"], "test.pdf")

    def test_upload_requires_staff(self):
        self.client.logout()
        f = SimpleUploadedFile("test.pdf", b"PDF content", content_type="application/pdf")
        response = self.client.post(reverse("bulk_email:attachment_upload"), {"file": f})
        self.assertNotEqual(response.status_code, 200)


class AttachmentDownloadTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_staff("staff3")
        self.client.login(username="staff3", password="pw")
        self.attachment = BulkEmailAttachment.objects.create(
            filename="doc.pdf",
            file=SimpleUploadedFile("doc.pdf", b"content"),
        )

    def test_download_returns_200_for_staff(self):
        response = self.client.get(reverse("bulk_email:attachment_download", args=[self.attachment.pk]))
        self.assertEqual(response.status_code, 200)

    def test_download_requires_staff(self):
        self.client.logout()
        response = self.client.get(reverse("bulk_email:attachment_download", args=[self.attachment.pk]))
        self.assertNotEqual(response.status_code, 200)
```

- [ ] **Step 2: Run to verify failure**

```bash
.venv/bin/python -m pytest apps/bulk_email/tests/test_views.py::AttachmentUploadTest apps/bulk_email/tests/test_views.py::AttachmentDownloadTest -v
```

Expected: FAIL.

- [ ] **Step 3: Implement upload and download views**

Add to `apps/bulk_email/views.py`:

```python
@method_decorator(staff_required, name="dispatch")
class BulkEmailAttachmentUploadView(View):
    def post(self, request):
        f = request.FILES.get("file")
        if not f:
            return JsonResponse({"error": "No file"}, status=400)
        attachment = BulkEmailAttachment.objects.create(
            filename=f.name,
            file=f,
        )
        return JsonResponse({"pk": attachment.pk, "filename": attachment.filename})


@method_decorator(staff_required, name="dispatch")
class BulkEmailAttachmentDownloadView(View):
    def get(self, request, pk):
        attachment = get_object_or_404(BulkEmailAttachment, pk=pk)
        response = FileResponse(attachment.file.open("rb"), as_attachment=True, filename=attachment.filename)
        return response
```

- [ ] **Step 4: Run tests**

```bash
.venv/bin/python -m pytest apps/bulk_email/tests/test_views.py::AttachmentUploadTest apps/bulk_email/tests/test_views.py::AttachmentDownloadTest -v
```

Expected: PASS.

- [ ] **Step 5: Create orphan cleanup management command**

```
apps/bulk_email/management/__init__.py  (empty)
apps/bulk_email/management/commands/__init__.py  (empty)
```

`apps/bulk_email/management/commands/cleanup_orphan_attachments.py`:

```python
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.bulk_email.models import BulkEmailAttachment


class Command(BaseCommand):
    help = "Delete BulkEmailAttachment records not linked to any BulkEmail and older than 24 hours"

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(hours=24)
        orphans = BulkEmailAttachment.objects.filter(bulk_email__isnull=True, uploaded_at__lt=cutoff)
        count = orphans.count()
        for attachment in orphans:
            attachment.file.delete(save=False)
            attachment.delete()
        self.stdout.write(f"Deleted {count} orphan attachment(s).")
```

- [ ] **Step 6: Commit**

```bash
git add apps/bulk_email/views.py apps/bulk_email/tests/test_views.py apps/bulk_email/management/
git commit -m "feat: add attachment upload, protected download, and orphan cleanup command"
```

---

## Task 9: Preview and Dry-Run AJAX Endpoints

**Files:**
- Modify: `apps/bulk_email/views.py`
- Create: `apps/bulk_email/templates/bulk_email/bulk_email_preview.html`
- Modify: `apps/bulk_email/tests/test_views.py`

- [ ] **Step 1: Write failing tests**

Add to `apps/bulk_email/tests/test_views.py`:

```python
class PreviewViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_staff("staff4")
        self.client.login(username="staff4", password="pw")
        self.school = School.objects.create(name="Preview Skole", signup_token="tok4", signup_password="pw4")
        Person.objects.create(school=self.school, name="KA", email="ka@s.dk", is_koordinator=True)

    def test_preview_renders_school_name(self):
        response = self.client.post(
            reverse("bulk_email:preview"),
            json.dumps({
                "school_pk": self.school.pk,
                "subject": "Hej {{ skole_navn }}",
                "body_html": "<p>Kære {{ kontakt_navn }}</p>",
                "recipient_type": BulkEmail.KOORDINATOR,
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Preview Skole")
        self.assertContains(response, "KA")

    def test_preview_returns_404_for_unknown_school(self):
        response = self.client.post(
            reverse("bulk_email:preview"),
            json.dumps({"school_pk": 99999, "subject": "x", "body_html": "x", "recipient_type": BulkEmail.KOORDINATOR}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)


class DryRunViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_staff("staff5")
        self.client.login(username="staff5", password="pw")
        self.school = School.objects.create(
            name="DryRun Skole", kommune="Vejle",
            enrolled_at="2024-08-01", active_from="2024-08-01",
            signup_token="tok5", signup_password="pw5",
        )
        Person.objects.create(school=self.school, name="KB", email="kb@s.dk", is_koordinator=True)

    def test_dry_run_returns_recipients(self):
        response = self.client.post(
            reverse("bulk_email:dry_run"),
            json.dumps({
                "recipient_type": BulkEmail.KOORDINATOR,
                "subject": "{{ skole_navn }}",
                "body_html": "",
                "filter_params": {"kommune": "Vejle"},
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("recipients", data)
        self.assertEqual(len(data["recipients"]), 1)
        self.assertEqual(data["recipients"][0]["school"], "DryRun Skole")

    def test_dry_run_reports_missing_fields(self):
        response = self.client.post(
            reverse("bulk_email:dry_run"),
            json.dumps({
                "recipient_type": BulkEmail.KOORDINATOR,
                "subject": "{{ ean_nummer }}",
                "body_html": "",
                "filter_params": {"kommune": "Vejle"},
            }),
            content_type="application/json",
        )
        data = json.loads(response.content)
        self.assertTrue(any("ean_nummer" in w["variable"] for w in data["warnings"]))
```

- [ ] **Step 2: Run to verify failure**

```bash
.venv/bin/python -m pytest apps/bulk_email/tests/test_views.py::PreviewViewTest apps/bulk_email/tests/test_views.py::DryRunViewTest -v
```

Expected: FAIL.

- [ ] **Step 3: Implement preview and dry-run views**

Add to `apps/bulk_email/views.py`:

```python
@method_decorator(staff_required, name="dispatch")
class BulkEmailPreviewView(View):
    def post(self, request):
        import json as _json
        data = _json.loads(request.body)
        school = get_object_or_404(__import__("apps.schools.models", fromlist=["School"]).School, pk=data.get("school_pk"))
        recipient_type = data.get("recipient_type", BulkEmail.KOORDINATOR)
        person = None
        if recipient_type == BulkEmail.KOORDINATOR:
            person = school.people.filter(is_koordinator=True, email__gt="").first()
        else:
            person = school.people.filter(is_oekonomisk_ansvarlig=True, email__gt="").first()
        subject = render_for_school(data.get("subject", ""), school, person)
        body_html = render_for_school(data.get("body_html", ""), school, person)
        from django.shortcuts import render as _render
        return _render(request, "bulk_email/bulk_email_preview.html", {
            "subject": subject,
            "body_html": body_html,
        })


@method_decorator(staff_required, name="dispatch")
class BulkEmailDryRunView(SchoolFilterMixin, View):
    def post(self, request):
        import json as _json
        data = _json.loads(request.body)
        recipient_type = data.get("recipient_type", BulkEmail.KOORDINATOR)
        filter_params = data.get("filter_params", {})
        subject_template = data.get("subject", "")
        body_template = data.get("body_html", "")

        # Build a fake request GET using filter_params dict
        from django.http import QueryDict
        from urllib.parse import urlencode
        fake_get = QueryDict(urlencode(filter_params), mutable=True)

        # Temporarily override request.GET for the mixin
        original_get = request.GET
        request.GET = fake_get
        schools = list(self.get_school_filter_queryset())  # materialise once
        request.GET = original_get

        school_person_pairs = resolve_recipients(schools, recipient_type)
        skipped = len(schools) - len(school_person_pairs)

        combined_template = subject_template + " " + body_template
        warnings = find_missing_variables(combined_template, school_person_pairs)

        recipients_out = [
            {"school": school.name, "person": person.name, "email": person.email}
            for school, person in school_person_pairs
        ]

        return JsonResponse({
            "recipients": recipients_out,
            "total": len(recipients_out),
            "skipped": skipped,
            "warnings": warnings,
        })
```

**Note:** The `DryRunView` receives filter_params in the POST body and applies them via the mixin. The `get_school_filter_queryset()` reads from `request.GET`, so we temporarily swap it in — this is safe because the view is synchronous.

- [ ] **Step 4: Create preview template**

`apps/bulk_email/templates/bulk_email/bulk_email_preview.html`:

```html
<!DOCTYPE html>
<html lang="da">
<head>
    <meta charset="UTF-8">
    <title>{{ subject }}</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; color: #333; }
        h2 { font-size: 1.1rem; color: #555; border-bottom: 1px solid #ddd; padding-bottom: 8px; }
    </style>
</head>
<body>
    <h2>Emne: {{ subject }}</h2>
    {{ body_html|safe }}
</body>
</html>
```

- [ ] **Step 5: Run tests**

```bash
.venv/bin/python -m pytest apps/bulk_email/tests/test_views.py::PreviewViewTest apps/bulk_email/tests/test_views.py::DryRunViewTest -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/bulk_email/views.py apps/bulk_email/templates/bulk_email/bulk_email_preview.html apps/bulk_email/tests/test_views.py
git commit -m "feat: add preview and dry-run AJAX endpoints"
```

---

## Task 10: SSE Send View

**Files:**
- Modify: `apps/bulk_email/views.py`
- Modify: `apps/bulk_email/tests/test_views.py`

- [ ] **Step 1: Write failing tests**

Add to `apps/bulk_email/tests/test_views.py`:

```python
from django.test import override_settings


@override_settings(RESEND_API_KEY=None)
class SendViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_staff("staff6")
        self.client.login(username="staff6", password="pw")
        self.school = School.objects.create(
            name="Send Skole", kommune="Odense",
            enrolled_at="2024-08-01", active_from="2024-08-01",
            signup_token="tok6", signup_password="pw6",
        )
        Person.objects.create(
            school=self.school, name="KC", email="kc@s.dk", is_koordinator=True
        )

    def _consume_stream(self, response):
        """Read all SSE events from a streaming response."""
        events = []
        for chunk in response.streaming_content:
            chunk_str = chunk.decode()
            for line in chunk_str.split("\n"):
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))
        return events

    def test_send_creates_bulk_email_record(self):
        response = self.client.post(
            reverse("bulk_email:send"),
            json.dumps({
                "subject": "Test",
                "body_html": "<p>Test</p>",
                "recipient_type": BulkEmail.KOORDINATOR,
                "filter_params": {"kommune": "Odense"},
                "attachment_pks": [],
            }),
            content_type="application/json",
        )
        list(response.streaming_content)  # exhaust stream
        self.assertEqual(BulkEmail.objects.count(), 1)

    def test_send_creates_recipient_records(self):
        response = self.client.post(
            reverse("bulk_email:send"),
            json.dumps({
                "subject": "Test",
                "body_html": "<p>Test</p>",
                "recipient_type": BulkEmail.KOORDINATOR,
                "filter_params": {"kommune": "Odense"},
                "attachment_pks": [],
            }),
            content_type="application/json",
        )
        list(response.streaming_content)
        self.assertEqual(BulkEmailRecipient.objects.count(), 1)

    def test_send_sets_sent_at(self):
        response = self.client.post(
            reverse("bulk_email:send"),
            json.dumps({
                "subject": "Test",
                "body_html": "<p>Test</p>",
                "recipient_type": BulkEmail.KOORDINATOR,
                "filter_params": {"kommune": "Odense"},
                "attachment_pks": [],
            }),
            content_type="application/json",
        )
        list(response.streaming_content)
        campaign = BulkEmail.objects.first()
        self.assertIsNotNone(campaign.sent_at)

    def test_send_emits_done_event(self):
        response = self.client.post(
            reverse("bulk_email:send"),
            json.dumps({
                "subject": "Test",
                "body_html": "<p>Test</p>",
                "recipient_type": BulkEmail.KOORDINATOR,
                "filter_params": {"kommune": "Odense"},
                "attachment_pks": [],
            }),
            content_type="application/json",
        )
        events = self._consume_stream(response)
        types = [e["type"] for e in events]
        self.assertIn("done", types)
```

- [ ] **Step 2: Run to verify failure**

```bash
.venv/bin/python -m pytest apps/bulk_email/tests/test_views.py::SendViewTest -v
```

Expected: FAIL.

- [ ] **Step 3: Implement SSE send view**

Add to `apps/bulk_email/views.py`:

```python
@method_decorator(staff_required, name="dispatch")
class BulkEmailSendView(SchoolFilterMixin, View):
    def post(self, request):
        import json as _json
        data = _json.loads(request.body)

        subject = data.get("subject", "")
        body_html = data.get("body_html", "")
        recipient_type = data.get("recipient_type", BulkEmail.KOORDINATOR)
        filter_params = data.get("filter_params", {})
        attachment_pks = data.get("attachment_pks", [])

        # Apply filters
        from django.http import QueryDict
        from urllib.parse import urlencode
        fake_get = QueryDict(urlencode(filter_params), mutable=True)
        original_get = request.GET
        request.GET = fake_get
        schools = list(self.get_school_filter_queryset())  # materialise once
        request.GET = original_get

        school_person_pairs = resolve_recipients(schools, recipient_type)

        # Create BulkEmail record
        campaign = BulkEmail.objects.create(
            subject=subject,
            body_html=body_html,
            recipient_type=recipient_type,
            filter_params=filter_params,
            sent_by=request.user,
        )

        # Link attachments
        if attachment_pks:
            BulkEmailAttachment.objects.filter(pk__in=attachment_pks).update(bulk_email=campaign)

        def event_stream():
            sent = 0
            failed = 0
            skipped = len(schools) - len(school_person_pairs)

            yield f"data: {_json.dumps({'type': 'start', 'total': len(school_person_pairs), 'skipped': skipped})}\n\n"

            for n, (school, person) in enumerate(school_person_pairs, start=1):
                recipient = send_to_school(campaign, school, person)
                if recipient.success:
                    sent += 1
                else:
                    failed += 1
                event = {
                    "type": "progress",
                    "n": n,
                    "total": len(school_person_pairs),
                    "school": school.name,
                    "email": recipient.email,
                    "success": recipient.success,
                    "error": recipient.error_message if not recipient.success else "",
                }
                yield f"data: {_json.dumps(event)}\n\n"

            campaign.sent_at = timezone.now()
            campaign.save(update_fields=["sent_at"])

            from django.urls import reverse as _reverse
            detail_url = _reverse("bulk_email:detail", args=[campaign.pk])
            yield f"data: {_json.dumps({'type': 'done', 'sent': sent, 'failed': failed, 'skipped': skipped, 'detail_url': detail_url})}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
```

- [ ] **Step 4: Run tests**

```bash
.venv/bin/python -m pytest apps/bulk_email/tests/test_views.py::SendViewTest -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/bulk_email/views.py apps/bulk_email/tests/test_views.py
git commit -m "feat: add SSE bulk email send view with streaming progress"
```

---

## Task 11: Composer Page

**Files:**
- Modify: `apps/bulk_email/views.py` (BulkEmailCreateView)
- Create: `apps/bulk_email/templates/bulk_email/bulk_email_create.html`
- Create: `apps/bulk_email/forms.py`

This is the main composer page. All the interactive pieces (filter, dry-run, preview, send) are wired together here. The JavaScript in this template drives the AJAX calls and SSE stream.

- [ ] **Step 1: Create form**

`apps/bulk_email/forms.py`:

```python
from django import forms
from django_summernote.widgets import SummernoteWidget
from apps.bulk_email.models import BulkEmail


class BulkEmailComposeForm(forms.Form):
    subject = forms.CharField(
        max_length=500,
        label="Emne",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Emne — brug {{ variabel }} for dynamisk indhold"}),
    )
    body_html = forms.CharField(
        label="Indhold",
        widget=SummernoteWidget(),
        required=False,
    )
    recipient_type = forms.ChoiceField(
        choices=BulkEmail.RECIPIENT_TYPE_CHOICES,
        label="Modtagertype",
        widget=forms.RadioSelect(),
        initial=BulkEmail.KOORDINATOR,
    )
```

- [ ] **Step 2: Implement BulkEmailCreateView**

Replace the stub in `apps/bulk_email/views.py`:

```python
@method_decorator(staff_required, name="dispatch")
class BulkEmailCreateView(SchoolFilterMixin, View):
    def get(self, request):
        from apps.bulk_email.forms import BulkEmailComposeForm
        from django.shortcuts import render as _render

        initial = {}
        copy_from_pk = request.GET.get("copy_from")
        copy_source = None
        if copy_from_pk:
            try:
                copy_source = BulkEmail.objects.get(pk=copy_from_pk)
                initial["subject"] = request.GET.get("subject", copy_source.subject)
                initial["body_html"] = copy_source.body_html
                initial["recipient_type"] = request.GET.get("recipient_type", copy_source.recipient_type)
            except BulkEmail.DoesNotExist:
                pass

        form = BulkEmailComposeForm(initial=initial)
        schools = list(self.get_school_filter_queryset())  # materialise once
        filter_context = self.get_filter_context()

        from apps.bulk_email.services import VARIABLE_NAMES
        context = {
            "form": form,
            "schools": schools[:200],  # limit picker to 200 for performance
            "total_matched": len(schools),
            "variable_names": VARIABLE_NAMES,
            "copy_source": copy_source,
            **filter_context,
        }
        return _render(request, "bulk_email/bulk_email_create.html", context)
```

- [ ] **Step 3: Create composer template**

`apps/bulk_email/templates/bulk_email/bulk_email_create.html` — this is large; create it with all five cards and the JavaScript:

```html
{% extends "core/base.html" %}

{% block title %}Ny masseudsendelse{% endblock %}

{% block content %}
<div class="container-fluid py-3">
    <h1 class="h3 mb-3">
        {% if copy_source %}Ny udsendelse — kopieret fra #{{ copy_source.pk }}{% else %}Ny udsendelse{% endif %}
    </h1>

    {# ── 1. Modtagere ───────────────────────────────────────── #}
    <div class="card mb-3">
        <div class="card-header fw-semibold">1. Modtagere</div>
        <div class="card-body">
            {% include 'schools/components/school_filter.html' %}

            <div class="mt-3 d-flex align-items-center gap-4">
                <div>
                    <label class="form-label fw-semibold mb-1">Modtagertype</label>
                    <div id="recipient-type-radios">
                        {% for value, label in form.recipient_type.field.choices %}
                        <div class="form-check form-check-inline">
                            <input class="form-check-input" type="radio" name="recipient_type"
                                   id="rt_{{ value }}" value="{{ value }}"
                                   {% if form.initial.recipient_type == value or forloop.first and not form.initial.recipient_type %}checked{% endif %}>
                            <label class="form-check-label" for="rt_{{ value }}">{{ label }}</label>
                        </div>
                        {% endfor %}
                    </div>
                </div>
                <div id="recipient-counter" class="text-muted small">Beregner...</div>
            </div>
        </div>
    </div>

    {# ── 2. Emne & indhold ──────────────────────────────────── #}
    <div class="card mb-3">
        <div class="card-header fw-semibold">2. Emne &amp; indhold</div>
        <div class="card-body">
            <div class="mb-3">
                <label for="id_subject" class="form-label">Emne</label>
                {{ form.subject }}
            </div>
            <div class="mb-3">
                <label class="form-label">Indhold</label>
                {{ form.body_html }}
            </div>

            {# Variable reference card #}
            <div class="accordion mb-3" id="varAccordion">
                <div class="accordion-item">
                    <h2 class="accordion-header">
                        <button class="accordion-button collapsed py-2" type="button"
                                data-bs-toggle="collapse" data-bs-target="#varList">
                            Tilgængelige variabler
                        </button>
                    </h2>
                    <div id="varList" class="accordion-collapse collapse">
                        <div class="accordion-body">
                            <div class="row">
                                {% for var in variable_names %}
                                <div class="col-md-4 col-sm-6 mb-1">
                                    <code class="user-select-all">{{ "{{" }} {{ var }} {{ "}}" }}</code>
                                </div>
                                {% endfor %}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {# Missing variable warnings #}
            <div id="variable-warnings"></div>
        </div>
    </div>

    {# ── 3. Vedhæftninger ───────────────────────────────────── #}
    <div class="card mb-3">
        <div class="card-header fw-semibold">3. Vedhæftninger</div>
        <div class="card-body">
            <input type="file" id="attachment-input" multiple class="form-control mb-2">
            <div id="attachment-list"></div>
        </div>
    </div>

    {# ── 4. Forhåndsvisning ─────────────────────────────────── #}
    <div class="card mb-3">
        <div class="card-header fw-semibold">4. Forhåndsvisning</div>
        <div class="card-body">
            <div class="mb-2">
                <label for="preview-school" class="form-label">Vælg skole til forhåndsvisning</label>
                <select id="preview-school" class="form-select">
                    <option value="">— Vælg skole —</option>
                    {% for school in schools %}
                    <option value="{{ school.pk }}">{{ school.name }}</option>
                    {% endfor %}
                </select>
            </div>
            <iframe id="preview-iframe" src="about:blank"
                    style="width:100%;height:500px;border:1px solid #dee2e6;border-radius:4px;"></iframe>
        </div>
    </div>

    {# ── 5. Afsendelse ──────────────────────────────────────── #}
    <div class="card mb-3">
        <div class="card-header fw-semibold">5. Afsendelse</div>
        <div class="card-body">

            {# Dry run #}
            <button type="button" id="dry-run-btn" class="btn btn-outline-secondary mb-3">
                Tør-kørsel
            </button>
            <div id="dry-run-panel" class="mb-3" style="display:none;"></div>

            {# Test email #}
            <div class="border rounded p-3 mb-3">
                <div class="row g-2 align-items-end">
                    <div class="col-md-4">
                        <label class="form-label">Send test-email til</label>
                        <input type="email" id="test-email-address" class="form-control" placeholder="din@email.dk">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Som om det er fra</label>
                        <select id="test-email-school" class="form-select">
                            {% for school in schools %}
                            <option value="{{ school.pk }}">{{ school.name }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-md-2">
                        <button type="button" id="test-email-btn" class="btn btn-outline-primary w-100">
                            Send test
                        </button>
                    </div>
                </div>
                <div id="test-email-result" class="mt-2"></div>
            </div>

            {# Send all #}
            <div id="send-panel">
                <button type="button" id="send-all-btn" class="btn btn-danger">
                    Send til alle
                </button>
            </div>

            {# Progress (hidden until send starts) #}
            <div id="send-progress" style="display:none;">
                <div class="progress mb-2" style="height:24px;">
                    <div id="progress-bar" class="progress-bar progress-bar-striped progress-bar-animated"
                         role="progressbar" style="width:0%">0%</div>
                </div>
                <div id="send-log" class="border rounded p-2 small" style="max-height:300px;overflow-y:auto;font-family:monospace;"></div>
            </div>
        </div>
    </div>
</div>

{# Confirmation modal #}
<div class="modal fade" id="sendConfirmModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Bekræft udsendelse</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body" id="modal-body-text"></div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annuller</button>
                <button type="button" class="btn btn-danger" id="confirm-send-btn">Send</button>
            </div>
        </div>
    </div>
</div>

{% endblock %}

{% block extra_js %}
<script>
const PREVIEW_URL = "{% url 'bulk_email:preview' %}";
const DRY_RUN_URL = "{% url 'bulk_email:dry_run' %}";
const SEND_URL = "{% url 'bulk_email:send' %}";
const UPLOAD_URL = "{% url 'bulk_email:attachment_upload' %}";
const CSRF_TOKEN = "{{ csrf_token }}";

// ── Attachment tracking ────────────────────────────────────────────
const uploadedAttachments = [];  // [{pk, filename}]

document.getElementById("attachment-input").addEventListener("change", async function() {
    for (const file of this.files) {
        const formData = new FormData();
        formData.append("file", file);
        const resp = await fetch(UPLOAD_URL, {
            method: "POST",
            headers: {"X-CSRFToken": CSRF_TOKEN},
            body: formData,
        });
        const data = await resp.json();
        uploadedAttachments.push({pk: data.pk, filename: data.filename});
        renderAttachmentList();
    }
    this.value = "";
});

function renderAttachmentList() {
    const list = document.getElementById("attachment-list");
    list.innerHTML = uploadedAttachments.map((a, i) =>
        `<div class="d-flex align-items-center gap-2 mb-1">
            <span>${a.filename}</span>
            <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeAttachment(${i})">✕</button>
        </div>`
    ).join("");
}

function removeAttachment(index) {
    uploadedAttachments.splice(index, 1);
    renderAttachmentList();
}

// ── Filter params helper ───────────────────────────────────────────
function getFilterParams() {
    const params = {};
    const urlParams = new URLSearchParams(window.location.search);
    for (const key of ["search", "year", "status_filter", "kommune", "unused_seats"]) {
        const val = urlParams.get(key) || "";
        if (val) params[key] = val;
    }
    return params;
}

function getRecipientType() {
    return document.querySelector('input[name="recipient_type"]:checked')?.value || "koordinator";
}

function getSubject() {
    return document.getElementById("id_subject").value;
}

function getBodyHtml() {
    // Summernote stores content in a textarea; get it via jQuery if available
    if (typeof $ !== "undefined" && $("#id_body_html").summernote) {
        return $("#id_body_html").summernote("code");
    }
    return document.getElementById("id_body_html")?.value || "";
}

// ── Recipient counter (via dry-run) ───────────────────────────────
let dryRunTimeout = null;

async function updateRecipientCounter() {
    const data = await fetchDryRun();
    const counter = document.getElementById("recipient-counter");
    if (data) {
        const typeLabel = getRecipientType() === "koordinator" ? "koordinator" : "økonomiansvarlig";
        counter.textContent = `${data.total} modtagere (${data.skipped} skoler uden ${typeLabel} sprunget over)`;
        renderWarnings(data.warnings);
    }
}

async function fetchDryRun() {
    try {
        const resp = await fetch(DRY_RUN_URL, {
            method: "POST",
            headers: {"X-CSRFToken": CSRF_TOKEN, "Content-Type": "application/json"},
            body: JSON.stringify({
                recipient_type: getRecipientType(),
                subject: getSubject(),
                body_html: getBodyHtml(),
                filter_params: getFilterParams(),
            }),
        });
        return await resp.json();
    } catch (e) {
        return null;
    }
}

function renderWarnings(warnings) {
    const el = document.getElementById("variable-warnings");
    if (!warnings || warnings.length === 0) {
        el.innerHTML = "";
        return;
    }
    el.innerHTML = `<div class="alert alert-warning mb-0 mt-2"><strong>Manglende felter:</strong><ul class="mb-0 mt-1">` +
        warnings.map(w => `<li><code>${w.variable}</code> mangler på: ${w.schools.join(", ")}</li>`).join("") +
        `</ul></div>`;
}

// Trigger counter update on filter change (filter auto-submits via GET, which reloads page)
// Also update when recipient type changes
document.querySelectorAll('input[name="recipient_type"]').forEach(r =>
    r.addEventListener("change", updateRecipientCounter)
);

// ── Preview ────────────────────────────────────────────────────────
let previewDebounce = null;

async function updatePreview() {
    const schoolPk = document.getElementById("preview-school").value;
    if (!schoolPk) return;
    const resp = await fetch(PREVIEW_URL, {
        method: "POST",
        headers: {"X-CSRFToken": CSRF_TOKEN, "Content-Type": "application/json"},
        body: JSON.stringify({
            school_pk: parseInt(schoolPk),
            subject: getSubject(),
            body_html: getBodyHtml(),
            recipient_type: getRecipientType(),
        }),
    });
    const html = await resp.text();
    const iframe = document.getElementById("preview-iframe");
    iframe.srcdoc = html;
}

document.getElementById("preview-school").addEventListener("change", updatePreview);

document.getElementById("id_subject").addEventListener("input", () => {
    clearTimeout(previewDebounce);
    previewDebounce = setTimeout(updatePreview, 800);
});

// Watch for Summernote changes
document.addEventListener("summernote.change", () => {
    clearTimeout(previewDebounce);
    previewDebounce = setTimeout(updatePreview, 800);
});

// ── Dry-run expand ────────────────────────────────────────────────
document.getElementById("dry-run-btn").addEventListener("click", async () => {
    const data = await fetchDryRun();
    const panel = document.getElementById("dry-run-panel");
    if (!data) {
        panel.innerHTML = '<div class="alert alert-danger">Kunne ikke hente tør-kørsel.</div>';
        panel.style.display = "block";
        return;
    }
    let html = `<div class="table-responsive"><table class="table table-sm table-bordered mb-0">
        <thead><tr><th>Skole</th><th>Kontakt</th><th>E-mail</th></tr></thead><tbody>`;
    for (const r of data.recipients) {
        html += `<tr><td>${r.school}</td><td>${r.person}</td><td>${r.email}</td></tr>`;
    }
    html += `</tbody></table></div>
    <p class="text-muted small mt-1">${data.total} modtagere · ${data.skipped} skoler sprunget over</p>`;
    panel.innerHTML = html;
    panel.style.display = "block";
    renderWarnings(data.warnings);
});

// ── Test email ────────────────────────────────────────────────────
document.getElementById("test-email-btn").addEventListener("click", async () => {
    const email = document.getElementById("test-email-address").value;
    const schoolPk = document.getElementById("test-email-school").value;
    const resultEl = document.getElementById("test-email-result");
    if (!email) {
        resultEl.innerHTML = '<span class="text-danger">Angiv en e-mailadresse.</span>';
        return;
    }
    const resp = await fetch("{% url 'bulk_email:send' %}", {
        method: "POST",
        headers: {"X-CSRFToken": CSRF_TOKEN, "Content-Type": "application/json"},
        body: JSON.stringify({
            subject: getSubject(),
            body_html: getBodyHtml(),
            recipient_type: getRecipientType(),
            filter_params: {},
            attachment_pks: uploadedAttachments.map(a => a.pk),
            test_email: email,
            test_school_pk: schoolPk ? parseInt(schoolPk) : null,
        }),
    });
    // Consume stream for test send (single recipient)
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
        const {done, value} = await reader.read();
        if (done) break;
        buffer += decoder.decode(value);
    }
    resultEl.innerHTML = '<span class="text-success">Test-email sendt.</span>';
});

// ── Send all ──────────────────────────────────────────────────────
document.getElementById("send-all-btn").addEventListener("click", async () => {
    const data = await fetchDryRun();
    const count = data ? data.total : "?";
    const filterSummary = "{{ filter_summary|escapejs }}";
    const summary = filterSummary ? `${filterSummary}` : "alle matchede skoler";
    document.getElementById("modal-body-text").textContent =
        `Du er ved at sende til ${count} modtagere (${summary}). Er du sikker?`;
    const modal = new bootstrap.Modal(document.getElementById("sendConfirmModal"));
    modal.show();
});

document.getElementById("confirm-send-btn").addEventListener("click", async () => {
    bootstrap.Modal.getInstance(document.getElementById("sendConfirmModal")).hide();
    document.getElementById("send-panel").style.display = "none";
    document.getElementById("send-progress").style.display = "block";

    const progressBar = document.getElementById("progress-bar");
    const sendLog = document.getElementById("send-log");

    const resp = await fetch(SEND_URL, {
        method: "POST",
        headers: {"X-CSRFToken": CSRF_TOKEN, "Content-Type": "application/json"},
        body: JSON.stringify({
            subject: getSubject(),
            body_html: getBodyHtml(),
            recipient_type: getRecipientType(),
            filter_params: getFilterParams(),
            attachment_pks: uploadedAttachments.map(a => a.pk),
        }),
    });

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let total = 0;

    while (true) {
        const {done, value} = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, {stream: true});
        const lines = buffer.split("\n");
        buffer = lines.pop();
        for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const event = JSON.parse(line.slice(6));
            if (event.type === "start") {
                total = event.total;
            } else if (event.type === "progress") {
                const pct = total > 0 ? Math.round((event.n / total) * 100) : 0;
                progressBar.style.width = pct + "%";
                progressBar.textContent = pct + "%";
                const icon = event.success ? "✓" : "✗";
                sendLog.innerHTML += `<div>${icon} ${event.school} &lt;${event.email}&gt;${event.error ? " — " + event.error : ""}</div>`;
                sendLog.scrollTop = sendLog.scrollHeight;
            } else if (event.type === "done") {
                progressBar.classList.remove("progress-bar-animated");
                progressBar.style.width = "100%";
                progressBar.textContent = "Afsluttet";
                sendLog.innerHTML += `<div class="mt-2 fw-bold">${event.sent} sendt · ${event.failed} fejlede · ${event.skipped} sprunget over — <a href="${event.detail_url}">Se detaljer</a></div>`;
            }
        }
    }
});

// ── Init ──────────────────────────────────────────────────────────
updateRecipientCounter();
</script>
{% endblock %}
```

- [ ] **Step 4: Handle test email in send view**

The send view needs to handle the `test_email` case. Modify `BulkEmailSendView.post()`:

After `data = _json.loads(request.body)`, add:

```python
# Test email path: send directly to one address without creating a BulkEmail record
test_email = data.get("test_email")
if test_email:
    import json as _json_te
    import resend as _resend
    from apps.schools.models import School as _School, Person as _Person
    from apps.emails.services import check_email_domain_allowed, EMAIL_FOOTER
    from apps.bulk_email.services import render_for_school

    test_school_pk = data.get("test_school_pk")
    if test_school_pk:
        try:
            school = _School.objects.prefetch_related("people").get(pk=test_school_pk)
            person = school.people.filter(email__gt="").first()
        except _School.DoesNotExist:
            school = _School(name="Test", signup_token="", signup_password="")
            person = None
    else:
        school = _School(name="Test", signup_token="", signup_password="")
        person = None

    fake_person = _Person(name="Test", email=test_email)
    rendered_subject = render_for_school(subject, school, person or fake_person)
    rendered_body = render_for_school(body_html, school, person or fake_person) + EMAIL_FOOTER

    def test_stream():
        success = True
        error = ""
        if not check_email_domain_allowed(test_email):
            success = False
            error = "[BLOCKED] Domain not in EMAIL_ALLOWED_DOMAINS"
        elif not getattr(settings, "RESEND_API_KEY", None):
            logger.info(f"[TEST EMAIL] DEV MODE — To: {test_email}")
        else:
            try:
                _resend.api_key = settings.RESEND_API_KEY
                _resend.Emails.send({
                    "from": settings.DEFAULT_FROM_EMAIL,
                    "to": [test_email],
                    "subject": rendered_subject,
                    "html": rendered_body,
                })
            except Exception as e:
                success = False
                error = str(e)[:200]
        yield f"data: {_json_te.dumps({'type': 'start', 'total': 1, 'skipped': 0})}\n\n"
        yield f"data: {_json_te.dumps({'type': 'progress', 'n': 1, 'total': 1, 'school': school.name, 'email': test_email, 'success': success, 'error': error})}\n\n"
        yield f"data: {_json_te.dumps({'type': 'done', 'sent': 1 if success else 0, 'failed': 0 if success else 1, 'skipped': 0, 'detail_url': ''})}\n\n"

    response = StreamingHttpResponse(test_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
```

This block must appear before the rest of the send logic. Note: test sends do **not** create a `BulkEmail` record and do not appear in campaign history.

- [ ] **Step 5: Add test for test-email path (no BulkEmail record created)**

Add to `apps/bulk_email/tests/test_views.py`:

```python
@override_settings(RESEND_API_KEY=None)
class TestEmailSendTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_staff("staff7")
        self.client.login(username="staff7", password="pw")
        self.school = School.objects.create(
            name="Test Afsender Skole", signup_token="tok7", signup_password="pw7"
        )

    def _consume_stream(self, response):
        events = []
        for chunk in response.streaming_content:
            for line in chunk.decode().split("\n"):
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))
        return events

    def test_test_email_does_not_create_bulk_email_record(self):
        response = self.client.post(
            reverse("bulk_email:send"),
            json.dumps({
                "subject": "Test",
                "body_html": "<p>x</p>",
                "recipient_type": BulkEmail.KOORDINATOR,
                "filter_params": {},
                "attachment_pks": [],
                "test_email": "test@example.com",
                "test_school_pk": self.school.pk,
            }),
            content_type="application/json",
        )
        list(response.streaming_content)
        self.assertEqual(BulkEmail.objects.count(), 0)

    def test_test_email_emits_done_event(self):
        response = self.client.post(
            reverse("bulk_email:send"),
            json.dumps({
                "subject": "Test",
                "body_html": "<p>x</p>",
                "recipient_type": BulkEmail.KOORDINATOR,
                "filter_params": {},
                "attachment_pks": [],
                "test_email": "test@example.com",
                "test_school_pk": self.school.pk,
            }),
            content_type="application/json",
        )
        events = self._consume_stream(response)
        types = [e["type"] for e in events]
        self.assertIn("done", types)
```

- [ ] **Step 6: Run all tests**

```bash
.venv/bin/python -m pytest apps/bulk_email/ -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/bulk_email/views.py apps/bulk_email/forms.py apps/bulk_email/templates/bulk_email/bulk_email_create.html apps/bulk_email/tests/test_views.py
git commit -m "feat: add composer page with filter, preview, dry-run, and SSE send"
```

---

## Task 12: Gunicorn gthread Workers

**Files:**
- Modify: `Dockerfile`

- [ ] **Step 1: Update Dockerfile CMD**

In `Dockerfile`, change:

```dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "config.wsgi:application"]
```

to:

```dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--worker-class", "gthread", "--threads", "4", "config.wsgi:application"]
```

- [ ] **Step 2: Verify Docker build succeeds (if Docker is available)**

```bash
docker build -t basal-test . 2>&1 | tail -5
```

If Docker is not available locally, this will be verified on deployment.

- [ ] **Step 3: Commit**

```bash
git add Dockerfile
git commit -m "chore: use gunicorn gthread workers to enable SSE streaming"
```

---

## Task 13: Run Full Test Suite and Final Check

- [ ] **Step 1: Run all bulk_email tests**

```bash
.venv/bin/python -m pytest apps/bulk_email/ -v
```

Expected: all pass.

- [ ] **Step 2: Run schools tests (verify mixin didn't break anything)**

```bash
.venv/bin/python -m pytest apps/schools/ -v
```

Expected: passes (known pre-existing failures in goals/core are unrelated).

- [ ] **Step 3: Run full suite**

```bash
.venv/bin/python -m pytest -x -q 2>&1 | tail -20
```

- [ ] **Step 4: Check for any ruff lint issues**

```bash
.venv/bin/python -m ruff check apps/bulk_email/ apps/schools/mixins.py
.venv/bin/python -m ruff format --check apps/bulk_email/ apps/schools/mixins.py
```

Fix any issues, then:

```bash
.venv/bin/python -m ruff format apps/bulk_email/ apps/schools/mixins.py
```

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore: lint fixes and final cleanup for bulk email component"
```

---

## Summary

| Task | What it builds |
|---|---|
| 1 | Merge better-school-filter branch |
| 2 | `SchoolFilterMixin` — shared filter logic + context |
| 3 | App scaffold — settings, URLs, nav |
| 4 | Models + migration |
| 5 | Audit registration |
| 6 | Services — template context, recipients, single send |
| 7 | List view + detail view + templates |
| 8 | Attachment upload, protected download, orphan cleanup |
| 9 | Preview and dry-run AJAX endpoints |
| 10 | SSE send stream view |
| 11 | Composer page (HTML + JS) |
| 12 | Gunicorn gthread workers |
| 13 | Full test run + lint |
