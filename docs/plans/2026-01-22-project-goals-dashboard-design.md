# Project Goals Dashboard Design

## Overview

A dashboard view showing the status and progress of the 5-year project milestones (2024/25 to 2028/29). The view matches the structure of the official project milestone table.

**Two components:**
1. **Front page summary** - current school year metrics (replaces existing metrics)
2. **Full detail page** - complete 5-year table with all metrics

## Data Model

### New Model: ProjectSettings

Singleton model for storing calculation multipliers, editable directly on the dashboard.

```python
# apps/core/models.py
class ProjectSettings(models.Model):
    """Singleton model for project-wide settings."""
    klasseforloeb_per_teacher_per_year = models.DecimalField(
        default=1.0,
        decimal_places=2,
        max_digits=4,
        verbose_name="Klasseforløb pr. lærer pr. år"
    )
    students_per_klasseforloeb = models.DecimalField(
        default=24.0,
        decimal_places=1,
        max_digits=5,
        verbose_name="Elever pr. klasseforløb"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Projektindstillinger"
        verbose_name_plural = "Projektindstillinger"

    def save(self, *args, **kwargs):
        self.pk = 1  # Singleton pattern
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
```

### CourseSignUp Model Addition

Add boolean to indicate if participant is a teacher (underviser):

```python
# apps/courses/models.py - add to CourseSignUp
is_underviser = models.BooleanField(
    default=True,
    verbose_name="Er underviser",
    help_text="Afkryds hvis deltageren er underviser (ikke leder/andet)"
)
```

Attendance tracking already exists via the roll-call feature.

## Hardcoded Targets

Fixed targets for the 5-year project span:

```python
# apps/goals/constants.py
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
```

## Calculation Logic

### School Year Helper

```python
# apps/goals/calculations.py
from datetime import date

def get_school_year(d: date) -> str:
    """Returns school year as string, e.g., '2024/25'.

    School year runs August 1 to July 31.
    """
    if d.month < 8:
        return f"{d.year - 1}/{str(d.year)[2:]}"
    return f"{d.year}/{str(d.year + 1)[2:]}"

def get_school_year_dates(year_str: str) -> tuple[date, date]:
    """Returns (start_date, end_date) for a school year string like '2024/25'."""
    start_year = int(year_str[:4])
    return (date(start_year, 8, 1), date(start_year + 1, 7, 31))

def get_current_school_year() -> str:
    """Returns the current school year."""
    return get_school_year(date.today())
```

### Metric Calculations

```python
# apps/goals/calculations.py
from apps.schools.models import School
from apps.courses.models import Course, CourseSignUp
from apps.core.models import ProjectSettings

def get_metrics_for_year(year_str: str) -> dict:
    """Calculate all metrics for a given school year."""
    start_date, end_date = get_school_year_dates(year_str)
    settings = ProjectSettings.get()

    # New school partnerships: enrolled this year
    new_schools = School.objects.filter(
        enrollment_date__gte=start_date,
        enrollment_date__lte=end_date
    ).count()

    # Anchoring: enrolled in previous year(s), still active
    anchoring_schools = School.objects.filter(
        enrollment_date__lt=start_date,
        is_active=True
    ).count()

    # Courses in this school year
    year_courses = Course.objects.filter(
        start_date__gte=start_date,
        start_date__lte=end_date
    )
    courses_count = year_courses.count()

    # Trained participants (attended = True via roll-call)
    trained_total = CourseSignUp.objects.filter(
        course__in=year_courses,
        attended=True
    ).count()

    # Trained teachers only
    trained_teachers = CourseSignUp.objects.filter(
        course__in=year_courses,
        attended=True,
        is_underviser=True
    ).count()

    # Calculated estimates
    klasseforloeb = trained_teachers * settings.klasseforloeb_per_teacher_per_year
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
```

## Views & URLs

### URL Structure

| URL | View | Purpose |
|-----|------|---------|
| `/` (existing) | `dashboard` | Updated with current year summary |
| `/projektmaal/` | `project_goals` | Full 5-year detail page |

### Navigation

- Front page summary includes "Se alle projektmål →" link
- User dropdown menu includes "Projektmål" link

### Cell Links (Drill-down)

Clicking on cells navigates to filtered list views:

| Cell Type | Link Pattern |
|-----------|--------------|
| New schools | `/schools/?school_year=2024-25&status=new` |
| Anchoring | `/schools/?school_year=2024-25&status=anchoring` |
| Courses | `/courses/?school_year=2024-25` |
| Trained participants | `/courses/signups/?school_year=2024-25&attended=true` |
| Trained teachers | `/courses/signups/?school_year=2024-25&attended=true&is_underviser=true` |

The klasseforløb and students cells are calculated values and not clickable.

## UI Design

### Front Page Summary Card

Replaces current metrics on the dashboard. Shows current school year only.

```
┌─────────────────────────────────────────────────────┐
│  Projektmål 2024/25                    Se alle →    │
├─────────────────────────────────────────────────────┤
│  Nye skoler          32 / 48    ████████░░░░  67%   │
│  Forankring          18 / 24    ██████████░░  75%   │
│  Kurser               5 / 7     ██████████░░  71%   │
│  Uddannede          120 / 168   ██████████░░  71%   │
└─────────────────────────────────────────────────────┘
```

### Full Detail Page

Table structure matching the original milestone table:

- Header row: Aktivitet/skoleår | 2024/25 | 2025/26 | 2026/27 | 2027/28 | 2028/29 | I alt
- Row backgrounds with light purple for section headers (matching original)
- Each cell shows target (styled as label) and actual value below
- Clickable cells are styled as links
- Footnotes displayed below table

### Multiplier Inputs

At top of detail page, with HTMX for save-without-reload:

```
┌─────────────────────────────────────────────────────┐
│  Beregningsgrundlag                                 │
│  Klasseforløb pr. lærer pr. år: [1.0 ]              │
│  Elever pr. klasseforløb:       [24  ]    [Gem]     │
└─────────────────────────────────────────────────────┘
```

## File Structure

### New Files

```
apps/
├── core/
│   └── models.py              # Add ProjectSettings model
│
├── courses/
│   ├── models.py              # Add is_underviser to CourseSignUp
│   └── forms.py               # Update signup form with is_underviser
│
└── goals/                     # New app
    ├── __init__.py
    ├── apps.py
    ├── admin.py               # Register ProjectSettings if needed
    ├── constants.py           # PROJECT_TARGETS, PROJECT_TOTALS
    ├── calculations.py        # Metric calculation functions
    ├── views.py               # project_goals view
    ├── urls.py                # /projektmaal/
    └── templates/goals/
        ├── project_goals.html         # Full detail page
        └── partials/
            └── settings_form.html     # HTMX partial for multiplier form
```

### Modified Files

```
apps/core/
├── views.py                   # Update dashboard to include summary
└── templates/core/
    └── dashboard.html         # Replace metrics with summary card

apps/schools/
└── views.py                   # Add school_year and status filters

apps/courses/
└── views.py                   # Add school_year filter

templates/
└── base.html                  # Add "Projektmål" to dropdown menu
```

## Filter Implementation

### Schools List Filters

Add query parameters to schools list view:

- `school_year` - filter by enrollment year (e.g., `2024-25`)
- `status` - `new` (enrolled this year) or `anchoring` (enrolled earlier)

### Courses List Filters

Add query parameter:

- `school_year` - filter by course start date year

### Signups List

May need a new view at `/courses/signups/` showing all signups across courses with filters:

- `school_year` - filter by course's school year
- `attended` - filter by attendance status
- `is_underviser` - filter by teacher status

## Footnotes

Display below the table on the detail page:

> \* For at sikre et godt udgangspunkt for drift og forankring efter projektets afslutning, udbydes flere kursuspladser til skolerne i 2027/28 end i 2024/25.
>
> \*\* Hertil kommer de forløb, tidligere uddannede lærere afholder.

## Testing

### Unit Tests

**Calculation tests** (`apps/goals/tests/test_calculations.py`):

- `test_get_school_year_august_onwards` - dates Aug-Dec return current/next year
- `test_get_school_year_before_august` - dates Jan-Jul return previous/current year
- `test_get_school_year_dates` - returns correct date range
- `test_new_schools_count` - counts schools enrolled in given year
- `test_anchoring_schools_count` - counts schools from previous years
- `test_trained_participants_excludes_no_shows` - only counts attended=True
- `test_trained_teachers_filters_by_is_underviser` - only counts is_underviser=True
- `test_klasseforloeb_calculation` - correct multiplication with setting
- `test_students_calculation` - correct multiplication with setting

**Model tests** (`apps/core/tests/test_models.py`):

- `test_project_settings_singleton` - only one instance can exist
- `test_project_settings_get_creates_default` - get() creates if not exists

### Integration Tests

**View tests** (`apps/goals/tests/test_views.py`):

- `test_project_goals_page_loads` - 200 response, correct template
- `test_project_goals_shows_all_years` - all 5 years present in response
- `test_project_goals_multiplier_update` - HTMX form saves settings
- `test_dashboard_shows_current_year_summary` - summary card present
- `test_cell_links_correct` - drill-down links have correct URLs

**Filter tests** (`apps/schools/tests/test_filters.py`, `apps/courses/tests/test_filters.py`):

- `test_schools_filter_by_school_year`
- `test_schools_filter_by_status_new`
- `test_schools_filter_by_status_anchoring`
- `test_courses_filter_by_school_year`
- `test_signups_filter_by_attended`
- `test_signups_filter_by_is_underviser`
