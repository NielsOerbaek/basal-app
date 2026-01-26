# Project Goals Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a milestone tracking dashboard showing 5-year project progress with a front-page summary and detailed view.

**Architecture:** New `goals` Django app with calculation functions. ProjectSettings model in `core` app for multiplier storage. Dashboard summary replaces current metrics. Detail page at `/projektmaal/` with clickable cells linking to filtered list views.

**Tech Stack:** Django 5, Bootstrap 5, HTMX for multiplier form updates.

---

## Task 1: Add is_underviser field to CourseSignUp

**Files:**
- Modify: `apps/courses/models.py:62-101`
- Create: `apps/courses/migrations/XXXX_add_is_underviser.py` (auto-generated)

**Step 1: Write the failing test**

Add to `apps/courses/tests.py`:

```python
from datetime import date
from django.test import TestCase
from apps.courses.models import Course, CourseSignUp, AttendanceStatus
from apps.schools.models import School


class CourseSignUpIsUnderTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name='Test School',
            adresse='Test Address',
            kommune='Test Kommune',
        )
        self.course = Course.objects.create(
            title='Test Course',
            start_date=date.today(),
            end_date=date.today(),
            location='Test Location',
        )

    def test_is_underviser_default_true(self):
        """CourseSignUp.is_underviser defaults to True."""
        signup = CourseSignUp.objects.create(
            school=self.school,
            course=self.course,
            participant_name='Test Person',
        )
        self.assertTrue(signup.is_underviser)

    def test_is_underviser_can_be_false(self):
        """CourseSignUp.is_underviser can be set to False."""
        signup = CourseSignUp.objects.create(
            school=self.school,
            course=self.course,
            participant_name='Test Leader',
            is_underviser=False,
        )
        self.assertFalse(signup.is_underviser)
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/courses/tests.py::CourseSignUpIsUnderTest -v`
Expected: FAIL with "CourseSignUp has no field 'is_underviser'"

**Step 3: Add field to model**

In `apps/courses/models.py`, add after `attendance` field (around line 87):

```python
    is_underviser = models.BooleanField(
        default=True,
        verbose_name='Er underviser',
        help_text='Afkryds hvis deltageren er underviser (ikke leder/andet)'
    )
```

**Step 4: Create and run migration**

Run: `python manage.py makemigrations courses -n add_is_underviser`
Run: `python manage.py migrate`

**Step 5: Run test to verify it passes**

Run: `pytest apps/courses/tests.py::CourseSignUpIsUnderTest -v`
Expected: PASS

**Step 6: Commit**

```bash
git add apps/courses/models.py apps/courses/migrations/
git commit -m "feat(courses): add is_underviser field to CourseSignUp"
```

---

## Task 2: Update CourseSignUp form to include is_underviser

**Files:**
- Modify: `apps/courses/forms.py`

**Step 1: Write the failing test**

Add to `apps/courses/tests.py`:

```python
class CourseSignUpFormTest(TestCase):
    def test_form_includes_is_underviser_field(self):
        """CourseSignUp form includes is_underviser field."""
        from apps.courses.forms import CourseSignUpForm
        form = CourseSignUpForm()
        self.assertIn('is_underviser', form.fields)
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/courses/tests.py::CourseSignUpFormTest -v`
Expected: FAIL

**Step 3: Update the form**

In `apps/courses/forms.py`, find the `CourseSignUpForm` class and add `is_underviser` to its fields.

First read the file to find exact location, then add `'is_underviser'` to the fields list.

**Step 4: Run test to verify it passes**

Run: `pytest apps/courses/tests.py::CourseSignUpFormTest -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/courses/forms.py
git commit -m "feat(courses): add is_underviser to signup form"
```

---

## Task 3: Create ProjectSettings model

**Files:**
- Create: `apps/core/models.py`
- Create: `apps/core/migrations/0001_initial.py` (auto-generated)

**Step 1: Write the failing test**

Add to `apps/core/tests.py`:

```python
class ProjectSettingsModelTest(TestCase):
    def test_singleton_pattern(self):
        """ProjectSettings enforces singleton pattern."""
        from apps.core.models import ProjectSettings
        settings1 = ProjectSettings.objects.create(
            klasseforloeb_per_teacher_per_year=1.5,
            students_per_klasseforloeb=20
        )
        settings2 = ProjectSettings.objects.create(
            klasseforloeb_per_teacher_per_year=2.0,
            students_per_klasseforloeb=25
        )
        # Should only have one record
        self.assertEqual(ProjectSettings.objects.count(), 1)
        # Should have the latest values
        settings = ProjectSettings.objects.first()
        self.assertEqual(settings.klasseforloeb_per_teacher_per_year, 2.0)

    def test_get_creates_default(self):
        """ProjectSettings.get() creates default if not exists."""
        from apps.core.models import ProjectSettings
        self.assertEqual(ProjectSettings.objects.count(), 0)
        settings = ProjectSettings.get()
        self.assertEqual(ProjectSettings.objects.count(), 1)
        self.assertEqual(settings.klasseforloeb_per_teacher_per_year, 1.0)
        self.assertEqual(settings.students_per_klasseforloeb, 24.0)

    def test_get_returns_existing(self):
        """ProjectSettings.get() returns existing instance."""
        from apps.core.models import ProjectSettings
        ProjectSettings.objects.create(
            klasseforloeb_per_teacher_per_year=3.0,
            students_per_klasseforloeb=30
        )
        settings = ProjectSettings.get()
        self.assertEqual(settings.klasseforloeb_per_teacher_per_year, 3.0)
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/core/tests.py::ProjectSettingsModelTest -v`
Expected: FAIL with "cannot import name 'ProjectSettings'"

**Step 3: Create the model**

Create `apps/core/models.py`:

```python
from django.db import models


class ProjectSettings(models.Model):
    """Singleton model for project-wide settings."""
    klasseforloeb_per_teacher_per_year = models.DecimalField(
        default=1.0,
        decimal_places=2,
        max_digits=4,
        verbose_name='Klasseforløb pr. lærer pr. år'
    )
    students_per_klasseforloeb = models.DecimalField(
        default=24.0,
        decimal_places=1,
        max_digits=5,
        verbose_name='Elever pr. klasseforløb'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Projektindstillinger'
        verbose_name_plural = 'Projektindstillinger'

    def save(self, *args, **kwargs):
        self.pk = 1  # Singleton pattern
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
```

**Step 4: Create and run migration**

Run: `python manage.py makemigrations core -n add_project_settings`
Run: `python manage.py migrate`

**Step 5: Run test to verify it passes**

Run: `pytest apps/core/tests.py::ProjectSettingsModelTest -v`
Expected: PASS

**Step 6: Commit**

```bash
git add apps/core/models.py apps/core/migrations/
git commit -m "feat(core): add ProjectSettings singleton model"
```

---

## Task 4: Create goals app with constants

**Files:**
- Create: `apps/goals/__init__.py`
- Create: `apps/goals/apps.py`
- Create: `apps/goals/constants.py`

**Step 1: Create app structure**

Run: `mkdir -p apps/goals`

**Step 2: Create __init__.py**

Create empty `apps/goals/__init__.py`

**Step 3: Create apps.py**

Create `apps/goals/apps.py`:

```python
from django.apps import AppConfig


class GoalsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.goals'
    verbose_name = 'Projektmål'
```

**Step 4: Create constants.py**

Create `apps/goals/constants.py`:

```python
"""
Hardcoded project targets for the 5-year span (2024/25 to 2028/29).
These values come from the official project milestone table.
"""

PROJECT_TARGETS = {
    "2024/25": {
        "new_schools": 48,
        "anchoring": 24,
        "courses": 7,
        "trained_total": 168,
        "trained_teachers": 120,
        "klasseforloeb_min": 120,
        "students_min": 2880,
    },
    "2025/26": {
        "new_schools": 48,
        "anchoring": 48,
        "courses": 8,
        "trained_total": 192,
        "trained_teachers": 144,
        "klasseforloeb_min": 144,
        "students_min": 3456,
    },
    "2026/27": {
        "new_schools": 48,
        "anchoring": 48,
        "courses": 8,
        "trained_total": 192,
        "trained_teachers": 144,
        "klasseforloeb_min": 144,
        "students_min": 3456,
    },
    "2027/28": {
        "new_schools": 48,
        "anchoring": 72,
        "courses": 9,
        "trained_total": 216,
        "trained_teachers": 168,
        "klasseforloeb_min": 168,
        "students_min": 4032,
    },
    "2028/29": {
        "new_schools": 24,
        "anchoring": 48,
        "courses": 5,
        "trained_total": 120,
        "trained_teachers": 96,
        "klasseforloeb_min": 96,
        "students_min": 2304,
    },
}

PROJECT_TOTALS = {
    "new_schools": 216,
    "anchoring": 240,
    "courses": 37,
    "trained_total": 888,
    "trained_teachers": 672,
    "klasseforloeb_min": 672,
    "students_min": 16128,
}

# School year boundaries
SCHOOL_YEAR_START_MONTH = 8  # August
SCHOOL_YEAR_START_DAY = 1
```

**Step 5: Register app in settings**

Add `'apps.goals'` to `INSTALLED_APPS` in `config/settings.py`.

**Step 6: Commit**

```bash
git add apps/goals/ config/settings.py
git commit -m "feat(goals): create goals app with project constants"
```

---

## Task 5: Create calculation functions

**Files:**
- Create: `apps/goals/calculations.py`
- Create: `apps/goals/tests.py`

**Step 1: Write the failing tests**

Create `apps/goals/tests.py`:

```python
from datetime import date
from decimal import Decimal

import pytest
from django.test import TestCase

from apps.courses.models import AttendanceStatus, Course, CourseSignUp
from apps.schools.models import School


class SchoolYearHelperTest(TestCase):
    def test_get_school_year_august_onwards(self):
        """Dates Aug-Dec return current/next school year."""
        from apps.goals.calculations import get_school_year
        self.assertEqual(get_school_year(date(2024, 8, 1)), "2024/25")
        self.assertEqual(get_school_year(date(2024, 12, 15)), "2024/25")

    def test_get_school_year_before_august(self):
        """Dates Jan-Jul return previous/current school year."""
        from apps.goals.calculations import get_school_year
        self.assertEqual(get_school_year(date(2025, 1, 15)), "2024/25")
        self.assertEqual(get_school_year(date(2025, 7, 31)), "2024/25")

    def test_get_school_year_dates(self):
        """get_school_year_dates returns correct date range."""
        from apps.goals.calculations import get_school_year_dates
        start, end = get_school_year_dates("2024/25")
        self.assertEqual(start, date(2024, 8, 1))
        self.assertEqual(end, date(2025, 7, 31))


class MetricsCalculationTest(TestCase):
    def setUp(self):
        # Create schools enrolled in 2024/25
        self.new_school = School.objects.create(
            name='New School',
            adresse='Address',
            kommune='Kommune',
            enrolled_at=date(2024, 9, 1)  # Enrolled in 2024/25
        )
        # Create school enrolled in previous year (anchoring)
        self.old_school = School.objects.create(
            name='Old School',
            adresse='Address',
            kommune='Kommune',
            enrolled_at=date(2023, 9, 1)  # Enrolled in 2023/24
        )
        # Create course in 2024/25
        self.course = Course.objects.create(
            title='Test Course',
            start_date=date(2024, 10, 1),
            end_date=date(2024, 10, 1),
            location='Location'
        )

    def test_new_schools_count(self):
        """Counts schools enrolled in given year."""
        from apps.goals.calculations import get_metrics_for_year
        metrics = get_metrics_for_year("2024/25")
        self.assertEqual(metrics['new_schools'], 1)

    def test_anchoring_schools_count(self):
        """Counts schools from previous years still active."""
        from apps.goals.calculations import get_metrics_for_year
        metrics = get_metrics_for_year("2024/25")
        self.assertEqual(metrics['anchoring'], 1)

    def test_courses_count(self):
        """Counts courses in given year."""
        from apps.goals.calculations import get_metrics_for_year
        metrics = get_metrics_for_year("2024/25")
        self.assertEqual(metrics['courses'], 1)

    def test_trained_participants_excludes_no_shows(self):
        """Only counts attended=PRESENT."""
        from apps.goals.calculations import get_metrics_for_year
        # Create signup that attended
        CourseSignUp.objects.create(
            school=self.new_school,
            course=self.course,
            participant_name='Attended',
            attendance=AttendanceStatus.PRESENT,
            is_underviser=True
        )
        # Create signup that didn't attend
        CourseSignUp.objects.create(
            school=self.new_school,
            course=self.course,
            participant_name='Absent',
            attendance=AttendanceStatus.ABSENT,
            is_underviser=True
        )
        metrics = get_metrics_for_year("2024/25")
        self.assertEqual(metrics['trained_total'], 1)

    def test_trained_teachers_filters_by_is_underviser(self):
        """Only counts is_underviser=True."""
        from apps.goals.calculations import get_metrics_for_year
        # Teacher
        CourseSignUp.objects.create(
            school=self.new_school,
            course=self.course,
            participant_name='Teacher',
            attendance=AttendanceStatus.PRESENT,
            is_underviser=True
        )
        # Leader
        CourseSignUp.objects.create(
            school=self.new_school,
            course=self.course,
            participant_name='Leader',
            attendance=AttendanceStatus.PRESENT,
            is_underviser=False
        )
        metrics = get_metrics_for_year("2024/25")
        self.assertEqual(metrics['trained_teachers'], 1)
        self.assertEqual(metrics['trained_total'], 2)


class EstimatedMetricsTest(TestCase):
    def setUp(self):
        from apps.core.models import ProjectSettings
        # Set custom multipliers
        ProjectSettings.objects.create(
            klasseforloeb_per_teacher_per_year=Decimal('2.0'),
            students_per_klasseforloeb=Decimal('20.0')
        )
        self.school = School.objects.create(
            name='School',
            adresse='Address',
            kommune='Kommune',
            enrolled_at=date(2024, 9, 1)
        )
        self.course = Course.objects.create(
            title='Course',
            start_date=date(2024, 10, 1),
            end_date=date(2024, 10, 1),
            location='Location'
        )
        # 3 teachers attended
        for i in range(3):
            CourseSignUp.objects.create(
                school=self.school,
                course=self.course,
                participant_name=f'Teacher {i}',
                attendance=AttendanceStatus.PRESENT,
                is_underviser=True
            )

    def test_klasseforloeb_calculation(self):
        """klasseforloeb = trained_teachers * multiplier."""
        from apps.goals.calculations import get_metrics_for_year
        metrics = get_metrics_for_year("2024/25")
        # 3 teachers * 2.0 = 6.0
        self.assertEqual(metrics['klasseforloeb'], Decimal('6.0'))

    def test_students_calculation(self):
        """students = klasseforloeb * students_per_klasseforloeb."""
        from apps.goals.calculations import get_metrics_for_year
        metrics = get_metrics_for_year("2024/25")
        # 6.0 klasseforloeb * 20.0 = 120.0
        self.assertEqual(metrics['students'], Decimal('120.0'))
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/goals/tests.py -v`
Expected: FAIL with "No module named 'apps.goals.calculations'"

**Step 3: Create calculations.py**

Create `apps/goals/calculations.py`:

```python
"""
Calculation functions for project goal metrics.
"""
from datetime import date
from decimal import Decimal

from apps.core.models import ProjectSettings
from apps.courses.models import AttendanceStatus, Course, CourseSignUp
from apps.schools.models import School

from .constants import SCHOOL_YEAR_START_DAY, SCHOOL_YEAR_START_MONTH


def get_school_year(d: date) -> str:
    """Returns school year as string, e.g., '2024/25'.

    School year runs August 1 to July 31.
    """
    if d.month < SCHOOL_YEAR_START_MONTH:
        return f"{d.year - 1}/{str(d.year)[2:]}"
    return f"{d.year}/{str(d.year + 1)[2:]}"


def get_school_year_dates(year_str: str) -> tuple[date, date]:
    """Returns (start_date, end_date) for a school year string like '2024/25'."""
    start_year = int(year_str[:4])
    return (
        date(start_year, SCHOOL_YEAR_START_MONTH, SCHOOL_YEAR_START_DAY),
        date(start_year + 1, SCHOOL_YEAR_START_MONTH - 1, 31)  # July 31
    )


def get_current_school_year() -> str:
    """Returns the current school year."""
    return get_school_year(date.today())


def get_metrics_for_year(year_str: str) -> dict:
    """Calculate all metrics for a given school year."""
    start_date, end_date = get_school_year_dates(year_str)
    settings = ProjectSettings.get()

    # New school partnerships: enrolled this year
    new_schools = School.objects.active().filter(
        enrolled_at__gte=start_date,
        enrolled_at__lte=end_date,
        opted_out_at__isnull=True
    ).count()

    # Anchoring: enrolled in previous year(s), still active in this year
    anchoring_schools = School.objects.active().filter(
        enrolled_at__lt=start_date,
        opted_out_at__isnull=True
    ).count()

    # Courses in this school year
    year_courses = Course.objects.filter(
        start_date__gte=start_date,
        start_date__lte=end_date
    )
    courses_count = year_courses.count()

    # Trained participants (attended = PRESENT via roll-call)
    trained_total = CourseSignUp.objects.filter(
        course__in=year_courses,
        attendance=AttendanceStatus.PRESENT
    ).count()

    # Trained teachers only
    trained_teachers = CourseSignUp.objects.filter(
        course__in=year_courses,
        attendance=AttendanceStatus.PRESENT,
        is_underviser=True
    ).count()

    # Calculated estimates
    klasseforloeb = Decimal(trained_teachers) * settings.klasseforloeb_per_teacher_per_year
    students = klasseforloeb * settings.students_per_klasseforloeb

    return {
        "new_schools": new_schools,
        "anchoring": anchoring_schools,
        "courses": courses_count,
        "trained_total": trained_total,
        "trained_teachers": trained_teachers,
        "klasseforloeb": klasseforloeb,
        "students": students,
    }


def get_all_years_metrics() -> dict:
    """Get metrics for all project years."""
    from .constants import PROJECT_TARGETS

    results = {}
    for year_str in PROJECT_TARGETS.keys():
        results[year_str] = get_metrics_for_year(year_str)
    return results
```

**Step 4: Run test to verify it passes**

Run: `pytest apps/goals/tests.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/goals/calculations.py apps/goals/tests.py
git commit -m "feat(goals): add calculation functions for project metrics"
```

---

## Task 6: Create project goals detail view

**Files:**
- Create: `apps/goals/views.py`
- Create: `apps/goals/urls.py`
- Create: `apps/goals/forms.py`
- Modify: `config/urls.py`

**Step 1: Write the failing test**

Add to `apps/goals/tests.py`:

```python
@pytest.mark.django_db
class ProjectGoalsViewTest:
    def test_project_goals_page_loads(self, staff_client):
        """Project goals page loads for staff."""
        from django.urls import reverse
        response = staff_client.get(reverse('goals:detail'))
        assert response.status_code == 200

    def test_project_goals_shows_all_years(self, staff_client):
        """All 5 project years are shown."""
        from django.urls import reverse
        response = staff_client.get(reverse('goals:detail'))
        assert '2024/25' in response.content.decode()
        assert '2028/29' in response.content.decode()

    def test_project_goals_requires_auth(self, client):
        """Project goals page requires authentication."""
        from django.urls import reverse
        response = client.get(reverse('goals:detail'))
        assert response.status_code == 302  # Redirect to login
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/goals/tests.py::ProjectGoalsViewTest -v`
Expected: FAIL with "No module named 'urls'"

**Step 3: Create forms.py**

Create `apps/goals/forms.py`:

```python
from django import forms

from apps.core.models import ProjectSettings


class ProjectSettingsForm(forms.ModelForm):
    class Meta:
        model = ProjectSettings
        fields = ['klasseforloeb_per_teacher_per_year', 'students_per_klasseforloeb']
        widgets = {
            'klasseforloeb_per_teacher_per_year': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.1', 'min': '0'}
            ),
            'students_per_klasseforloeb': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '1', 'min': '0'}
            ),
        }
```

**Step 4: Create views.py**

Create `apps/goals/views.py`:

```python
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView

from apps.core.decorators import staff_required
from apps.core.models import ProjectSettings

from .calculations import get_all_years_metrics, get_current_school_year, get_metrics_for_year
from .constants import PROJECT_TARGETS, PROJECT_TOTALS
from .forms import ProjectSettingsForm


@method_decorator(staff_required, name='dispatch')
class ProjectGoalsView(TemplateView):
    template_name = 'goals/project_goals.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get settings and form
        settings = ProjectSettings.get()
        context['settings_form'] = ProjectSettingsForm(instance=settings)

        # Get metrics for all years
        all_metrics = get_all_years_metrics()

        # Build table data
        years = list(PROJECT_TARGETS.keys())
        context['years'] = years
        context['targets'] = PROJECT_TARGETS
        context['totals'] = PROJECT_TOTALS
        context['metrics'] = all_metrics
        context['current_year'] = get_current_school_year()

        return context


@method_decorator(staff_required, name='dispatch')
class UpdateSettingsView(View):
    def post(self, request):
        settings = ProjectSettings.get()
        form = ProjectSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)
```

**Step 5: Create urls.py**

Create `apps/goals/urls.py`:

```python
from django.urls import path

from . import views

app_name = 'goals'

urlpatterns = [
    path('', views.ProjectGoalsView.as_view(), name='detail'),
    path('settings/', views.UpdateSettingsView.as_view(), name='update-settings'),
]
```

**Step 6: Register URLs in config/urls.py**

Add to `config/urls.py` after the other app includes:

```python
    path("projektmaal/", include("apps.goals.urls")),
```

**Step 7: Run test to verify it passes**

Run: `pytest apps/goals/tests.py::ProjectGoalsViewTest -v`
Expected: FAIL (template doesn't exist yet - that's Task 7)

**Step 8: Commit**

```bash
git add apps/goals/views.py apps/goals/urls.py apps/goals/forms.py config/urls.py
git commit -m "feat(goals): add project goals views and URLs"
```

---

## Task 7: Create project goals template

**Files:**
- Create: `apps/goals/templates/goals/project_goals.html`

**Step 1: Create template directory**

Run: `mkdir -p apps/goals/templates/goals`

**Step 2: Create the template**

Create `apps/goals/templates/goals/project_goals.html`:

```html
{% extends 'core/base.html' %}

{% block title %}Projektmål - Basal{% endblock %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h1><i class="bi bi-bullseye me-2"></i>Projektmål</h1>
</div>

<!-- Settings form -->
<div class="card mb-4">
    <div class="card-header">
        <i class="bi bi-gear me-2"></i>Beregningsgrundlag
    </div>
    <div class="card-body">
        <form id="settings-form" hx-post="{% url 'goals:update-settings' %}" hx-swap="none">
            {% csrf_token %}
            <div class="row g-3 align-items-end">
                <div class="col-auto">
                    <label class="form-label">Klasseforløb pr. lærer pr. år</label>
                    {{ settings_form.klasseforloeb_per_teacher_per_year }}
                </div>
                <div class="col-auto">
                    <label class="form-label">Elever pr. klasseforløb</label>
                    {{ settings_form.students_per_klasseforloeb }}
                </div>
                <div class="col-auto">
                    <button type="submit" class="btn btn-primary">
                        <i class="bi bi-check-lg me-1"></i>Gem
                    </button>
                </div>
            </div>
        </form>
    </div>
</div>

<!-- Main table -->
<div class="card">
    <div class="card-body">
        <div class="table-responsive">
            <table class="table table-bordered mb-0">
                <thead>
                    <tr class="table-light">
                        <th>Aktivitet/skoleår</th>
                        {% for year in years %}
                        <th class="text-center {% if year == current_year %}table-primary{% endif %}">{{ year }}</th>
                        {% endfor %}
                        <th class="text-center">I alt</th>
                    </tr>
                </thead>
                <tbody>
                    <!-- New schools -->
                    <tr>
                        <td>Etablering af samarbejde med nye skoler</td>
                        {% for year in years %}
                        <td class="text-center {% if year == current_year %}table-primary{% endif %}">
                            <a href="{% url 'schools:list' %}?school_year={{ year }}&status=new">
                                <strong>{{ metrics|get_item:year|get_item:'new_schools' }}</strong>
                                <span class="text-muted">/ {{ targets|get_item:year|get_item:'new_schools' }}</span>
                            </a>
                        </td>
                        {% endfor %}
                        <td class="text-center">
                            <strong>{{ totals.new_schools }}</strong>
                        </td>
                    </tr>

                    <!-- Anchoring schools -->
                    <tr>
                        <td>Forankring i eksisterende skoler</td>
                        {% for year in years %}
                        <td class="text-center {% if year == current_year %}table-primary{% endif %}">
                            <a href="{% url 'schools:list' %}?school_year={{ year }}&status=anchoring">
                                <strong>{{ metrics|get_item:year|get_item:'anchoring' }}</strong>
                                <span class="text-muted">/ {{ targets|get_item:year|get_item:'anchoring' }}</span>
                            </a>
                        </td>
                        {% endfor %}
                        <td class="text-center">
                            <strong>{{ totals.anchoring }}</strong>
                        </td>
                    </tr>

                    <!-- Courses header -->
                    <tr class="table-secondary">
                        <td colspan="{{ years|length|add:2 }}"><strong>Antal kurser</strong></td>
                    </tr>

                    <!-- Courses row -->
                    <tr>
                        <td class="ps-4">24 deltagere pr. kursus</td>
                        {% for year in years %}
                        <td class="text-center {% if year == current_year %}table-primary{% endif %}">
                            <a href="{% url 'courses:list' %}?school_year={{ year }}">
                                <strong>{{ metrics|get_item:year|get_item:'courses' }}</strong>
                                <span class="text-muted">/ {{ targets|get_item:year|get_item:'courses' }}</span>
                            </a>
                        </td>
                        {% endfor %}
                        <td class="text-center">
                            <strong>{{ totals.courses }}</strong>
                        </td>
                    </tr>

                    <!-- Trained total/teachers -->
                    <tr>
                        <td>Uddannede i alt / undervisere</td>
                        {% for year in years %}
                        <td class="text-center {% if year == current_year %}table-primary{% endif %}">
                            <a href="{% url 'courses:signup-list' %}?school_year={{ year }}&attended=true">
                                <strong>{{ metrics|get_item:year|get_item:'trained_total' }}/{{ metrics|get_item:year|get_item:'trained_teachers' }}</strong>
                            </a>
                            <br>
                            <span class="text-muted small">mål: {{ targets|get_item:year|get_item:'trained_total' }}/{{ targets|get_item:year|get_item:'trained_teachers' }}</span>
                        </td>
                        {% endfor %}
                        <td class="text-center">
                            <strong>{{ totals.trained_total }}/{{ totals.trained_teachers }}</strong>
                        </td>
                    </tr>

                    <!-- Estimated klasseforløb -->
                    <tr>
                        <td>Estimerede antal klasseforløb</td>
                        {% for year in years %}
                        <td class="text-center {% if year == current_year %}table-primary{% endif %}">
                            <strong>{{ metrics|get_item:year|get_item:'klasseforloeb'|floatformat:0 }}</strong>
                            <span class="text-muted">/ min. {{ targets|get_item:year|get_item:'klasseforloeb_min' }}</span>
                        </td>
                        {% endfor %}
                        <td class="text-center">
                            <strong>Min. {{ totals.klasseforloeb_min }}</strong>
                        </td>
                    </tr>

                    <!-- Estimated students -->
                    <tr>
                        <td>Estimerede antal elever</td>
                        {% for year in years %}
                        <td class="text-center {% if year == current_year %}table-primary{% endif %}">
                            <strong>{{ metrics|get_item:year|get_item:'students'|floatformat:0 }}</strong>
                            <span class="text-muted">/ min. {{ targets|get_item:year|get_item:'students_min' }}</span>
                        </td>
                        {% endfor %}
                        <td class="text-center">
                            <strong>Min. {{ totals.students_min }}</strong>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- Footnotes -->
        <div class="mt-3 small text-muted">
            <p class="mb-1">* For at sikre et godt udgangspunkt for drift og forankring efter projektets afslutning, udbydes flere kursuspladser til skolerne i 2027/28 end i 2024/25.</p>
            <p class="mb-0">** Hertil kommer de forløb, tidligere uddannede lærere afholder.</p>
        </div>
    </div>
</div>
{% endblock %}
```

**Step 3: Create template tag for dict access**

Create `apps/goals/templatetags/__init__.py` and `apps/goals/templatetags/goals_tags.py`:

```python
# apps/goals/templatetags/goals_tags.py
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key in template."""
    if dictionary is None:
        return None
    return dictionary.get(key)
```

**Step 4: Run test to verify it passes**

Run: `pytest apps/goals/tests.py::ProjectGoalsViewTest -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/goals/templates/ apps/goals/templatetags/
git commit -m "feat(goals): add project goals template and tags"
```

---

## Task 8: Update dashboard with summary card

**Files:**
- Modify: `apps/core/views.py`
- Modify: `apps/core/templates/core/dashboard.html`

**Step 1: Write the failing test**

Add to `apps/core/tests.py`:

```python
class DashboardSummaryTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123", is_staff=True)

    def test_dashboard_shows_project_goals_summary(self):
        """Dashboard should show project goals summary card."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("core:dashboard"))
        self.assertContains(response, "Projektmål")
        self.assertContains(response, "Se alle")
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/core/tests.py::DashboardSummaryTest -v`
Expected: FAIL

**Step 3: Update DashboardView**

In `apps/core/views.py`, update `get_context_data`:

```python
from apps.goals.calculations import get_current_school_year, get_metrics_for_year
from apps.goals.constants import PROJECT_TARGETS

# In get_context_data, add:
        # Project goals summary for current year
        current_year = get_current_school_year()
        context['current_school_year'] = current_year
        context['goals_metrics'] = get_metrics_for_year(current_year)
        context['goals_targets'] = PROJECT_TARGETS.get(current_year, {})
```

**Step 4: Update dashboard template**

Replace the stats row in `apps/core/templates/core/dashboard.html` with the project goals summary card:

```html
<!-- Project Goals Summary Card -->
<div class="card mb-4">
    <div class="card-header d-flex justify-content-between align-items-center">
        <span><i class="bi bi-bullseye me-2"></i>Projektmål {{ current_school_year }}</span>
        <a href="{% url 'goals:detail' %}" class="btn btn-sm btn-outline-primary">Se alle <i class="bi bi-arrow-right"></i></a>
    </div>
    <div class="card-body">
        <div class="row">
            <div class="col-md-3">
                <div class="mb-2">
                    <small class="text-muted">Nye skoler</small>
                    <div class="d-flex align-items-center">
                        <strong class="me-2">{{ goals_metrics.new_schools }} / {{ goals_targets.new_schools }}</strong>
                        {% widthratio goals_metrics.new_schools goals_targets.new_schools 100 as pct %}
                        <div class="progress flex-grow-1" style="height: 8px;">
                            <div class="progress-bar" style="width: {{ pct }}%"></div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="mb-2">
                    <small class="text-muted">Forankring</small>
                    <div class="d-flex align-items-center">
                        <strong class="me-2">{{ goals_metrics.anchoring }} / {{ goals_targets.anchoring }}</strong>
                        {% widthratio goals_metrics.anchoring goals_targets.anchoring 100 as pct %}
                        <div class="progress flex-grow-1" style="height: 8px;">
                            <div class="progress-bar" style="width: {{ pct }}%"></div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="mb-2">
                    <small class="text-muted">Kurser</small>
                    <div class="d-flex align-items-center">
                        <strong class="me-2">{{ goals_metrics.courses }} / {{ goals_targets.courses }}</strong>
                        {% widthratio goals_metrics.courses goals_targets.courses 100 as pct %}
                        <div class="progress flex-grow-1" style="height: 8px;">
                            <div class="progress-bar" style="width: {{ pct }}%"></div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="mb-2">
                    <small class="text-muted">Uddannede</small>
                    <div class="d-flex align-items-center">
                        <strong class="me-2">{{ goals_metrics.trained_total }} / {{ goals_targets.trained_total }}</strong>
                        {% widthratio goals_metrics.trained_total goals_targets.trained_total 100 as pct %}
                        <div class="progress flex-grow-1" style="height: 8px;">
                            <div class="progress-bar" style="width: {{ pct }}%"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
```

**Step 5: Run test to verify it passes**

Run: `pytest apps/core/tests.py::DashboardSummaryTest -v`
Expected: PASS

**Step 6: Commit**

```bash
git add apps/core/views.py apps/core/templates/core/dashboard.html
git commit -m "feat(core): add project goals summary to dashboard"
```

---

## Task 9: Add Projektmål to dropdown menu

**Files:**
- Modify: `apps/core/templates/core/base.html`

**Step 1: Update base template**

In `apps/core/templates/core/base.html`, add after the "Skoleår" dropdown item (around line 117):

```html
<li><a class="dropdown-item" href="{% url 'goals:detail' %}"><i class="bi bi-bullseye me-2"></i>Projektmål</a></li>
```

**Step 2: Commit**

```bash
git add apps/core/templates/core/base.html
git commit -m "feat(core): add Projektmål to user dropdown menu"
```

---

## Task 10: Add school year filters to schools list

**Files:**
- Modify: `apps/schools/views.py`

**Step 1: Write the failing test**

Add to `apps/schools/tests.py`:

```python
class SchoolYearFilterTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True
        )
        # School enrolled in 2024/25
        self.new_school = School.objects.create(
            name='New School 2024',
            adresse='Address',
            kommune='Kommune',
            enrolled_at=date(2024, 9, 1)
        )
        # School enrolled in 2023/24 (anchoring in 2024/25)
        self.old_school = School.objects.create(
            name='Old School 2023',
            adresse='Address',
            kommune='Kommune',
            enrolled_at=date(2023, 9, 1)
        )

    def test_filter_by_school_year_new(self):
        """Filter schools by school year and new status."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('schools:list'), {
            'school_year': '2024/25',
            'status': 'new'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'New School 2024')
        self.assertNotContains(response, 'Old School 2023')

    def test_filter_by_school_year_anchoring(self):
        """Filter schools by school year and anchoring status."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('schools:list'), {
            'school_year': '2024/25',
            'status': 'anchoring'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Old School 2023')
        self.assertNotContains(response, 'New School 2024')
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/schools/tests.py::SchoolYearFilterTest -v`
Expected: FAIL

**Step 3: Update SchoolListView**

In `apps/schools/views.py`, update `get_base_queryset` method in `SchoolListView` to add school year and status filters:

```python
        # School year and status filter (for project goals drilldown)
        school_year = self.request.GET.get("school_year")
        status = self.request.GET.get("status")
        if school_year and status:
            from apps.goals.calculations import get_school_year_dates
            start_date, end_date = get_school_year_dates(school_year)
            if status == "new":
                queryset = queryset.filter(
                    enrolled_at__gte=start_date,
                    enrolled_at__lte=end_date
                )
            elif status == "anchoring":
                queryset = queryset.filter(
                    enrolled_at__lt=start_date
                )
```

**Step 4: Run test to verify it passes**

Run: `pytest apps/schools/tests.py::SchoolYearFilterTest -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/schools/views.py
git commit -m "feat(schools): add school_year and status filters for goals drilldown"
```

---

## Task 11: Add school year filter to courses list

**Files:**
- Modify: `apps/courses/views.py`

**Step 1: Write the failing test**

Add to `apps/courses/tests.py`:

```python
class CourseSchoolYearFilterTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True
        )
        # Course in 2024/25
        self.course_2024 = Course.objects.create(
            title='Course 2024',
            start_date=date(2024, 10, 1),
            end_date=date(2024, 10, 1),
            location='Location'
        )
        # Course in 2025/26
        self.course_2025 = Course.objects.create(
            title='Course 2025',
            start_date=date(2025, 10, 1),
            end_date=date(2025, 10, 1),
            location='Location'
        )

    def test_filter_courses_by_school_year(self):
        """Filter courses by school year."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('courses:list'), {
            'school_year': '2024/25'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Course 2024')
        self.assertNotContains(response, 'Course 2025')
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/courses/tests.py::CourseSchoolYearFilterTest -v`
Expected: FAIL

**Step 3: Update CourseListView**

Find CourseListView in `apps/courses/views.py` and add school year filter to its queryset method:

```python
        # School year filter (for project goals drilldown)
        school_year = self.request.GET.get("school_year")
        if school_year:
            from apps.goals.calculations import get_school_year_dates
            start_date, end_date = get_school_year_dates(school_year)
            queryset = queryset.filter(
                start_date__gte=start_date,
                start_date__lte=end_date
            )
```

**Step 4: Run test to verify it passes**

Run: `pytest apps/courses/tests.py::CourseSchoolYearFilterTest -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/courses/views.py
git commit -m "feat(courses): add school_year filter for goals drilldown"
```

---

## Task 12: Add filters to signup list

**Files:**
- Modify: `apps/courses/views.py`

**Step 1: Write the failing test**

Add to `apps/courses/tests.py`:

```python
class SignupFilterTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True
        )
        self.school = School.objects.create(
            name='Test School',
            adresse='Address',
            kommune='Kommune'
        )
        self.course = Course.objects.create(
            title='Course',
            start_date=date(2024, 10, 1),
            end_date=date(2024, 10, 1),
            location='Location'
        )
        # Attended teacher
        self.teacher = CourseSignUp.objects.create(
            school=self.school,
            course=self.course,
            participant_name='Teacher',
            attendance=AttendanceStatus.PRESENT,
            is_underviser=True
        )
        # Non-attended
        self.absent = CourseSignUp.objects.create(
            school=self.school,
            course=self.course,
            participant_name='Absent Person',
            attendance=AttendanceStatus.ABSENT,
            is_underviser=True
        )

    def test_filter_signups_by_attended(self):
        """Filter signups by attended status."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('courses:signup-list'), {
            'attended': 'true'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Teacher')
        self.assertNotContains(response, 'Absent Person')
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/courses/tests.py::SignupFilterTest -v`
Expected: FAIL

**Step 3: Update CourseSignUpListView**

Find CourseSignUpListView in `apps/courses/views.py` and add filters:

```python
        # Attended filter
        attended = self.request.GET.get("attended")
        if attended == "true":
            queryset = queryset.filter(attendance=AttendanceStatus.PRESENT)

        # Underviser filter
        is_underviser = self.request.GET.get("is_underviser")
        if is_underviser == "true":
            queryset = queryset.filter(is_underviser=True)

        # School year filter
        school_year = self.request.GET.get("school_year")
        if school_year:
            from apps.goals.calculations import get_school_year_dates
            start_date, end_date = get_school_year_dates(school_year)
            queryset = queryset.filter(
                course__start_date__gte=start_date,
                course__start_date__lte=end_date
            )
```

**Step 4: Run test to verify it passes**

Run: `pytest apps/courses/tests.py::SignupFilterTest -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/courses/views.py
git commit -m "feat(courses): add attended, is_underviser, school_year filters to signup list"
```

---

## Task 13: Run full test suite

**Step 1: Run all tests**

Run: `pytest -v`
Expected: All tests PASS

**Step 2: Fix any failures**

If any tests fail, fix them before proceeding.

**Step 3: Commit any fixes**

```bash
git add -A
git commit -m "fix: resolve test failures"
```

---

## Task 14: Manual verification

**Step 1: Start development server**

Run: `python manage.py runserver`

**Step 2: Verify dashboard**

- Visit `http://localhost:8000/`
- Confirm project goals summary card appears
- Confirm progress bars show correct values

**Step 3: Verify project goals page**

- Click "Se alle" or visit `http://localhost:8000/projektmaal/`
- Confirm all 5 years are shown
- Confirm metrics update when changing multipliers
- Confirm clicking cells navigates to filtered lists

**Step 4: Verify dropdown menu**

- Confirm "Projektmål" appears in user dropdown
- Confirm link works

**Step 5: Commit**

```bash
git add -A
git commit -m "chore: manual verification complete"
```
