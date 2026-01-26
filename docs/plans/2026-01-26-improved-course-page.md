# Improved Course Page Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor course management to use auto-generated names, managed instructor/location lists, editable signups, and enhanced bulk import.

**Architecture:** Add Instructor and Location models with admin management. Replace Course title/location/undervisere fields with relationships. Add signup edit modal and extend bulk import to 6 columns. Use HTMX for dynamic form interactions.

**Tech Stack:** Django 5, PostgreSQL, HTMX, Crispy Forms, Bootstrap 5

---

## Task 1: Create Instructor Model

**Files:**
- Modify: `apps/courses/models.py`
- Test: `apps/courses/tests.py`

**Step 1: Write the failing test**

Add to `apps/courses/tests.py`:

```python
class InstructorModelTest(TestCase):
    def test_create_instructor(self):
        """Instructor model can be created with a name."""
        from apps.courses.models import Instructor
        instructor = Instructor.objects.create(name="Anders Andersen")
        self.assertEqual(instructor.name, "Anders Andersen")
        self.assertEqual(str(instructor), "Anders Andersen")

    def test_instructor_name_unique(self):
        """Instructor names must be unique."""
        from apps.courses.models import Instructor
        Instructor.objects.create(name="Anders Andersen")
        with self.assertRaises(IntegrityError):
            Instructor.objects.create(name="Anders Andersen")
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/courses/tests.py::InstructorModelTest -v`
Expected: FAIL with "cannot import name 'Instructor'"

**Step 3: Write minimal implementation**

Add to `apps/courses/models.py` after the AttendanceStatus class:

```python
class Instructor(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="Navn")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Underviser"
        verbose_name_plural = "Undervisere"

    def __str__(self):
        return self.name
```

**Step 4: Create and run migration**

Run: `python manage.py makemigrations courses --name add_instructor_model && python manage.py migrate`

**Step 5: Run test to verify it passes**

Run: `pytest apps/courses/tests.py::InstructorModelTest -v`
Expected: PASS

**Step 6: Commit**

```bash
git add apps/courses/models.py apps/courses/migrations/ apps/courses/tests.py
git commit -m "$(cat <<'EOF'
feat(courses): add Instructor model

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Create Location Model

**Files:**
- Modify: `apps/courses/models.py`
- Test: `apps/courses/tests.py`

**Step 1: Write the failing test**

Add to `apps/courses/tests.py`:

```python
class LocationModelTest(TestCase):
    def test_create_location(self):
        """Location model can be created with address details."""
        from apps.courses.models import Location
        location = Location.objects.create(
            name="Basal Hovedkontor",
            street_address="Vesterbrogade 123",
            postal_code="1620",
            municipality="København V"
        )
        self.assertEqual(location.name, "Basal Hovedkontor")
        self.assertEqual(str(location), "Basal Hovedkontor")

    def test_location_full_address(self):
        """Location.full_address returns formatted address."""
        from apps.courses.models import Location
        location = Location.objects.create(
            name="Basal Hovedkontor",
            street_address="Vesterbrogade 123",
            postal_code="1620",
            municipality="København V"
        )
        self.assertEqual(
            location.full_address,
            "Basal Hovedkontor, Vesterbrogade 123, 1620 København V"
        )

    def test_location_full_address_minimal(self):
        """Location.full_address works with only name."""
        from apps.courses.models import Location
        location = Location.objects.create(name="Online")
        self.assertEqual(location.full_address, "Online")

    def test_location_address_fields_optional(self):
        """Location can be created with only name."""
        from apps.courses.models import Location
        location = Location.objects.create(name="Online")
        self.assertEqual(location.street_address, "")
        self.assertEqual(location.postal_code, "")
        self.assertEqual(location.municipality, "")
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/courses/tests.py::LocationModelTest -v`
Expected: FAIL with "cannot import name 'Location'"

**Step 3: Write minimal implementation**

Add to `apps/courses/models.py` after the Instructor class:

```python
class Location(models.Model):
    name = models.CharField(max_length=255, verbose_name="Navn")
    street_address = models.CharField(max_length=255, blank=True, verbose_name="Adresse")
    postal_code = models.CharField(max_length=10, blank=True, verbose_name="Postnummer")
    municipality = models.CharField(max_length=100, blank=True, verbose_name="By")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Lokation"
        verbose_name_plural = "Lokationer"

    def __str__(self):
        return self.name

    @property
    def full_address(self):
        """Returns formatted full address."""
        parts = [self.name]
        if self.street_address:
            parts.append(self.street_address)
        if self.postal_code or self.municipality:
            parts.append(f"{self.postal_code} {self.municipality}".strip())
        return ", ".join(parts)
```

**Step 4: Create and run migration**

Run: `python manage.py makemigrations courses --name add_location_model && python manage.py migrate`

**Step 5: Run test to verify it passes**

Run: `pytest apps/courses/tests.py::LocationModelTest -v`
Expected: PASS

**Step 6: Commit**

```bash
git add apps/courses/models.py apps/courses/migrations/ apps/courses/tests.py
git commit -m "$(cat <<'EOF'
feat(courses): add Location model with full_address property

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Register Instructor and Location in Admin

**Files:**
- Modify: `apps/courses/admin.py`

**Step 1: Update admin.py**

Replace contents of `apps/courses/admin.py`:

```python
from django.contrib import admin

from .models import Course, CourseSignUp, Instructor, Location


@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ["name", "created_at"]
    search_fields = ["name"]


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ["name", "street_address", "postal_code", "municipality", "created_at"]
    search_fields = ["name", "street_address", "municipality"]


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["title", "start_date", "end_date", "location", "undervisere", "capacity", "signup_count", "is_published"]
    list_filter = ["is_published", "start_date"]
    search_fields = ["title", "location", "undervisere"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(CourseSignUp)
class CourseSignUpAdmin(admin.ModelAdmin):
    list_display = ["participant_name", "school", "course", "attendance", "created_at"]
    list_filter = ["attendance", "course", "created_at"]
    search_fields = ["participant_name", "school__name", "course__title"]
    raw_id_fields = ["school", "course"]
```

**Step 2: Verify admin works**

Run: `python manage.py check`
Expected: System check identified no issues.

**Step 3: Commit**

```bash
git add apps/courses/admin.py
git commit -m "$(cat <<'EOF'
feat(courses): register Instructor and Location in admin

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Add New Fields to Course Model

**Files:**
- Modify: `apps/courses/models.py`
- Test: `apps/courses/tests.py`

**Step 1: Write the failing test**

Add to `apps/courses/tests.py`:

```python
class CourseNewFieldsTest(TestCase):
    def test_course_with_location_fk(self):
        """Course can have a Location foreign key."""
        from apps.courses.models import Location
        location = Location.objects.create(name="Test Location")
        course = Course.objects.create(
            title="Test Course",
            start_date=date.today(),
            end_date=date.today(),
            location="Legacy",
            location_new=location,
        )
        self.assertEqual(course.location_new, location)

    def test_course_with_instructors(self):
        """Course can have multiple instructors."""
        from apps.courses.models import Instructor
        i1 = Instructor.objects.create(name="Anders")
        i2 = Instructor.objects.create(name="Bente")
        course = Course.objects.create(
            title="Test Course",
            start_date=date.today(),
            end_date=date.today(),
            location="Test",
        )
        course.instructors.add(i1, i2)
        self.assertEqual(course.instructors.count(), 2)
        self.assertIn(i1, course.instructors.all())
        self.assertIn(i2, course.instructors.all())
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/courses/tests.py::CourseNewFieldsTest -v`
Expected: FAIL with "Course has no field named 'location_new'" or similar

**Step 3: Write minimal implementation**

Add new fields to the Course model in `apps/courses/models.py`. Add these after the `is_published` field:

```python
    location_new = models.ForeignKey(
        "Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses",
        verbose_name="Lokation",
    )
    instructors = models.ManyToManyField(
        "Instructor",
        blank=True,
        related_name="courses",
        verbose_name="Undervisere",
    )
```

**Step 4: Create and run migration**

Run: `python manage.py makemigrations courses --name add_course_location_fk_and_instructors && python manage.py migrate`

**Step 5: Run test to verify it passes**

Run: `pytest apps/courses/tests.py::CourseNewFieldsTest -v`
Expected: PASS

**Step 6: Commit**

```bash
git add apps/courses/models.py apps/courses/migrations/ apps/courses/tests.py
git commit -m "$(cat <<'EOF'
feat(courses): add location_new FK and instructors M2M to Course

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Add display_name Property to Course

**Files:**
- Modify: `apps/courses/models.py`
- Test: `apps/courses/tests.py`

**Step 1: Write the failing test**

Add to `apps/courses/tests.py`:

```python
class CourseDisplayNameTest(TestCase):
    def test_display_name_single_day(self):
        """Course.display_name shows single date for same-day course."""
        course = Course.objects.create(
            title="Old Title",
            start_date=date(2026, 1, 15),
            end_date=date(2026, 1, 15),
            location="Test",
        )
        self.assertIn("Kompetenceudviklingskursus", course.display_name)
        self.assertIn("15", course.display_name)
        self.assertIn("jan", course.display_name.lower())
        self.assertIn("2026", course.display_name)
        self.assertNotIn("-", course.display_name.split(",")[1])  # No date range

    def test_display_name_multi_day(self):
        """Course.display_name shows date range for multi-day course."""
        course = Course.objects.create(
            title="Old Title",
            start_date=date(2026, 1, 15),
            end_date=date(2026, 1, 17),
            location="Test",
        )
        self.assertIn("Kompetenceudviklingskursus", course.display_name)
        self.assertIn("15", course.display_name)
        self.assertIn("17", course.display_name)
        self.assertIn("-", course.display_name)
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/courses/tests.py::CourseDisplayNameTest -v`
Expected: FAIL with "Course has no attribute 'display_name'"

**Step 3: Write minimal implementation**

Add to the Course class in `apps/courses/models.py`, after the `is_past` property:

```python
    @property
    def display_name(self):
        """Auto-generated course name with dates."""
        import locale
        try:
            locale.setlocale(locale.LC_TIME, "da_DK.UTF-8")
        except locale.Error:
            pass  # Fall back to default locale

        if self.start_date == self.end_date:
            date_str = self.start_date.strftime("%-d. %b %Y").lower()
        else:
            start_str = self.start_date.strftime("%-d. %b").lower()
            end_str = self.end_date.strftime("%-d. %b %Y").lower()
            date_str = f"{start_str} - {end_str}"
        return f"Kompetenceudviklingskursus, {date_str}"
```

**Step 4: Run test to verify it passes**

Run: `pytest apps/courses/tests.py::CourseDisplayNameTest -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/courses/models.py apps/courses/tests.py
git commit -m "$(cat <<'EOF'
feat(courses): add display_name property with auto-generated name

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Data Migration - Migrate Existing Instructors and Locations

**Files:**
- Create: `apps/courses/migrations/XXXX_migrate_instructors_locations.py`

**Step 1: Create data migration**

Run: `python manage.py makemigrations courses --empty --name migrate_instructors_locations`

**Step 2: Write the migration**

Edit the created migration file:

```python
from django.db import migrations


def migrate_data(apps, schema_editor):
    Course = apps.get_model("courses", "Course")
    Instructor = apps.get_model("courses", "Instructor")
    Location = apps.get_model("courses", "Location")

    # Migrate instructors
    for course in Course.objects.exclude(undervisere=""):
        names = [n.strip() for n in course.undervisere.split(",") if n.strip()]
        for name in names:
            instructor, _ = Instructor.objects.get_or_create(name=name)
            course.instructors.add(instructor)

    # Migrate locations
    for course in Course.objects.exclude(location=""):
        location, _ = Location.objects.get_or_create(name=course.location)
        course.location_new = location
        course.save()


def reverse_migrate(apps, schema_editor):
    Course = apps.get_model("courses", "Course")

    for course in Course.objects.all():
        # Restore undervisere from instructors
        instructor_names = list(course.instructors.values_list("name", flat=True))
        course.undervisere = ", ".join(instructor_names)

        # Restore location from location_new
        if course.location_new:
            course.location = course.location_new.name

        course.save()


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "PREVIOUS_MIGRATION"),  # Update this to actual previous migration name
    ]

    operations = [
        migrations.RunPython(migrate_data, reverse_migrate),
    ]
```

**Step 3: Update the migration dependency**

Edit the file to set the correct previous migration name.

**Step 4: Run the migration**

Run: `python manage.py migrate courses`

**Step 5: Verify migration worked**

Run: `python manage.py shell -c "from apps.courses.models import Instructor, Location; print(f'Instructors: {Instructor.objects.count()}, Locations: {Location.objects.count()}')"`

**Step 6: Commit**

```bash
git add apps/courses/migrations/
git commit -m "$(cat <<'EOF'
feat(courses): data migration for instructors and locations

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Remove Old Fields from Course Model

**Files:**
- Modify: `apps/courses/models.py`
- Modify: `apps/courses/admin.py`

**Step 1: Update Course model**

In `apps/courses/models.py`, remove these fields from the Course class:
- `title`
- `undervisere`
- `location` (the CharField)

Rename `location_new` to `location`.

Update the `__str__` method:

```python
    def __str__(self):
        return self.display_name
```

**Step 2: Update admin.py**

Update `apps/courses/admin.py` CourseAdmin:

```python
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["display_name", "start_date", "end_date", "location", "capacity", "signup_count", "is_published"]
    list_filter = ["is_published", "start_date"]
    search_fields = ["location__name"]
    readonly_fields = ["created_at", "updated_at"]
    filter_horizontal = ["instructors"]
```

**Step 3: Create migration**

Run: `python manage.py makemigrations courses --name remove_old_course_fields && python manage.py migrate`

**Step 4: Update existing tests**

Update tests in `apps/courses/tests.py` that reference `title` or `location` CharField. Replace:
- `title="..."` with appropriate handling (remove or use display_name)
- `location="..."` with creating a Location object first

**Step 5: Run all tests**

Run: `pytest apps/courses/ -v`
Expected: All tests pass

**Step 6: Commit**

```bash
git add apps/courses/models.py apps/courses/admin.py apps/courses/migrations/ apps/courses/tests.py
git commit -m "$(cat <<'EOF'
feat(courses): remove title/undervisere fields, rename location_new to location

BREAKING: Course.title removed, use display_name property
BREAKING: Course.location is now FK to Location model

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Update Course Form with Instructor/Location Dropdowns

**Files:**
- Modify: `apps/courses/forms.py`
- Create: `apps/courses/templates/courses/partials/add_instructor_fields.html`
- Create: `apps/courses/templates/courses/partials/add_location_fields.html`

**Step 1: Update CourseForm**

Replace CourseForm in `apps/courses/forms.py`:

```python
class CourseForm(forms.ModelForm):
    instructor_1 = forms.ModelChoiceField(
        queryset=Instructor.objects.all(),
        required=True,
        label="Underviser 1",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    instructor_2 = forms.ModelChoiceField(
        queryset=Instructor.objects.all(),
        required=False,
        label="Underviser 2",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    instructor_3 = forms.ModelChoiceField(
        queryset=Instructor.objects.all(),
        required=False,
        label="Underviser 3",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    new_instructor_1 = forms.CharField(required=False, label="Ny underviser 1")
    new_instructor_2 = forms.CharField(required=False, label="Ny underviser 2")
    new_instructor_3 = forms.CharField(required=False, label="Ny underviser 3")

    new_location_name = forms.CharField(required=False, label="Lokationsnavn")
    new_location_street = forms.CharField(required=False, label="Adresse")
    new_location_postal = forms.CharField(required=False, label="Postnummer")
    new_location_municipality = forms.CharField(required=False, label="By")

    class Meta:
        model = Course
        fields = ["start_date", "end_date", "location", "capacity", "is_published", "comment"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "end_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["location"].required = False
        self.fields["location"].empty_label = "Vælg lokation..."

        # Add "add new" option indicator
        self.fields["instructor_1"].empty_label = "Vælg underviser..."
        self.fields["instructor_2"].empty_label = "Vælg underviser..."
        self.fields["instructor_3"].empty_label = "Vælg underviser..."

        # Pre-populate instructors if editing
        if self.instance.pk:
            instructors = list(self.instance.instructors.all()[:3])
            for i, instructor in enumerate(instructors, 1):
                self.fields[f"instructor_{i}"].initial = instructor

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column("start_date", css_class="col-md-6"),
                Column("end_date", css_class="col-md-6"),
            ),
            "location",
            HTML('<div id="new-location-fields" style="display:none;" class="card card-body bg-light mb-3"></div>'),
            Row(
                Column("instructor_1", css_class="col-md-4"),
                Column("instructor_2", css_class="col-md-4"),
                Column("instructor_3", css_class="col-md-4"),
            ),
            HTML('<div id="new-instructor-fields"></div>'),
            "capacity",
            "is_published",
            "comment",
        )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError("Slutdato kan ikke være før startdato.")

        # Handle new location
        if cleaned_data.get("new_location_name"):
            location = Location.objects.create(
                name=cleaned_data["new_location_name"],
                street_address=cleaned_data.get("new_location_street", ""),
                postal_code=cleaned_data.get("new_location_postal", ""),
                municipality=cleaned_data.get("new_location_municipality", ""),
            )
            cleaned_data["location"] = location

        # Handle new instructors
        for i in range(1, 4):
            new_name = cleaned_data.get(f"new_instructor_{i}")
            if new_name:
                instructor, _ = Instructor.objects.get_or_create(name=new_name)
                cleaned_data[f"instructor_{i}"] = instructor

        # Require at least one instructor
        if not any(cleaned_data.get(f"instructor_{i}") for i in range(1, 4)):
            raise forms.ValidationError("Mindst én underviser er påkrævet.")

        return cleaned_data

    def save(self, commit=True):
        course = super().save(commit=commit)
        if commit:
            # Clear and re-add instructors
            course.instructors.clear()
            for i in range(1, 4):
                instructor = self.cleaned_data.get(f"instructor_{i}")
                if instructor:
                    course.instructors.add(instructor)
        return course
```

Add import at top:
```python
from .models import Course, CourseMaterial, CourseSignUp, Instructor, Location
```

**Step 2: Run tests**

Run: `pytest apps/courses/ -v`

**Step 3: Commit**

```bash
git add apps/courses/forms.py
git commit -m "$(cat <<'EOF'
feat(courses): update CourseForm with instructor/location dropdowns

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Update Course Form Template

**Files:**
- Modify: `apps/courses/templates/courses/course_form.html`

**Step 1: Read current template**

First, check the current course_form.html content.

**Step 2: Update template**

Update `apps/courses/templates/courses/course_form.html` to add JavaScript for "add new" functionality:

```html
{% extends 'core/base.html' %}
{% load crispy_forms_tags %}

{% block title %}{% if form.instance.pk %}Rediger kursus{% else %}Opret kursus{% endif %} - Basal{% endblock %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h1>
        <i class="bi bi-calendar-event me-2"></i>
        {% if form.instance.pk %}Rediger kursus{% else %}Opret nyt kursus{% endif %}
    </h1>
</div>

<div class="card">
    <div class="card-body">
        <form method="post">
            {% csrf_token %}
            {% crispy form %}

            <div class="mt-4">
                <button type="submit" class="btn btn-primary">
                    <i class="bi bi-check-lg me-1"></i>Gem
                </button>
                <a href="{% if form.instance.pk %}{% url 'courses:detail' form.instance.pk %}{% else %}{% url 'courses:list' %}{% endif %}" class="btn btn-outline-secondary">
                    Annuller
                </a>
            </div>
        </form>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
document.addEventListener('DOMContentLoaded', function() {
    // Add "Tilføj ny" option to location dropdown
    const locationSelect = document.getElementById('id_location');
    if (locationSelect) {
        const addNewOption = document.createElement('option');
        addNewOption.value = '__new__';
        addNewOption.textContent = '+ Tilføj ny lokation...';
        locationSelect.appendChild(addNewOption);

        locationSelect.addEventListener('change', function() {
            const newFields = document.getElementById('new-location-fields');
            if (this.value === '__new__') {
                newFields.style.display = 'block';
                newFields.innerHTML = `
                    <h6>Ny lokation</h6>
                    <div class="row">
                        <div class="col-md-6 mb-2">
                            <label class="form-label">Navn *</label>
                            <input type="text" name="new_location_name" class="form-control" required>
                        </div>
                        <div class="col-md-6 mb-2">
                            <label class="form-label">Adresse</label>
                            <input type="text" name="new_location_street" class="form-control">
                        </div>
                        <div class="col-md-6 mb-2">
                            <label class="form-label">Postnummer</label>
                            <input type="text" name="new_location_postal" class="form-control">
                        </div>
                        <div class="col-md-6 mb-2">
                            <label class="form-label">By</label>
                            <input type="text" name="new_location_municipality" class="form-control">
                        </div>
                    </div>
                `;
            } else {
                newFields.style.display = 'none';
                newFields.innerHTML = '';
            }
        });
    }

    // Add "Tilføj ny" option to instructor dropdowns
    ['id_instructor_1', 'id_instructor_2', 'id_instructor_3'].forEach(function(id, index) {
        const select = document.getElementById(id);
        if (select) {
            const addNewOption = document.createElement('option');
            addNewOption.value = '__new__';
            addNewOption.textContent = '+ Tilføj ny underviser...';
            select.appendChild(addNewOption);

            select.addEventListener('change', function() {
                const containerId = 'new-instructor-' + (index + 1);
                let container = document.getElementById(containerId);

                if (this.value === '__new__') {
                    if (!container) {
                        container = document.createElement('div');
                        container.id = containerId;
                        container.className = 'mb-2';
                        document.getElementById('new-instructor-fields').appendChild(container);
                    }
                    container.innerHTML = `
                        <label class="form-label">Ny underviser ${index + 1}</label>
                        <input type="text" name="new_instructor_${index + 1}" class="form-control" placeholder="Indtast navn">
                    `;
                } else if (container) {
                    container.remove();
                }
            });
        }
    });
});
</script>
{% endblock %}
```

**Step 3: Commit**

```bash
git add apps/courses/templates/courses/course_form.html
git commit -m "$(cat <<'EOF'
feat(courses): update course form template with add-new JS

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Update Course Detail Template

**Files:**
- Modify: `apps/courses/templates/courses/course_detail.html`

**Step 1: Update template**

Update `apps/courses/templates/courses/course_detail.html`:

1. Change header from `{{ course.title }}` to `{{ course.display_name }}`
2. Remove "Dato" row (it's now in the title)
3. Update "Sted" to show `{{ course.location.full_address }}`
4. Update "Undervisere" to list instructors
5. Add phone column to participants table
6. Add edit button to each participant row

Key changes:

Header:
```html
<h1><i class="bi bi-calendar-event me-2"></i>{{ course.display_name }}</h1>
```

Course info (remove Dato row, update Sted and Undervisere):
```html
<dt class="col-sm-4">Sted</dt>
<dd class="col-sm-8">{{ course.location.full_address|default:"-" }}</dd>
<dt class="col-sm-4">Undervisere</dt>
<dd class="col-sm-8">
    {% for instructor in course.instructors.all %}
        {{ instructor.name }}{% if not forloop.last %}, {% endif %}
    {% empty %}
        -
    {% endfor %}
</dd>
```

Participants table header:
```html
<tr>
    <th>Navn</th>
    <th>E-mail</th>
    <th>Telefon</th>
    <th>Titel</th>
    <th>Underviser</th>
    <th>Skole</th>
    <th>Fremmøde</th>
    <th></th>
</tr>
```

Participants table row (add phone and edit button):
```html
<td>
    {% if signup.participant_phone %}
    <a href="tel:{{ signup.participant_phone }}">{{ signup.participant_phone }}</a>
    {% else %}
    <span class="text-muted">-</span>
    {% endif %}
</td>
```

Action column:
```html
<td class="text-end">
    <button type="button" class="btn btn-sm btn-link text-primary p-0 me-2" title="Rediger tilmelding"
            hx-get="{% url 'courses:signup-edit' signup.pk %}"
            hx-target="#modal-container">
        <i class="bi bi-pencil"></i>
    </button>
    <button type="button" class="btn btn-sm btn-link text-danger p-0" title="Slet tilmelding"
            hx-get="{% url 'courses:signup-delete' signup.pk %}"
            hx-target="#modal-container">
        <i class="bi bi-x-lg"></i>
    </button>
</td>
```

Update colspan in empty row to 8.

**Step 2: Commit**

```bash
git add apps/courses/templates/courses/course_detail.html
git commit -m "$(cat <<'EOF'
feat(courses): update course detail with display_name, phone, edit button

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: Add Signup Edit View and Template

**Files:**
- Modify: `apps/courses/views.py`
- Modify: `apps/courses/forms.py`
- Create: `apps/courses/templates/courses/signup_edit_modal.html`
- Modify: `apps/courses/urls.py`
- Test: `apps/courses/tests.py`

**Step 1: Write the failing test**

Add to `apps/courses/tests.py`:

```python
class SignupEditViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123", is_staff=True)
        self.client.login(username="testuser", password="testpass123")
        self.school = School.objects.create(name="Test School", adresse="Test", kommune="Test")
        self.school2 = School.objects.create(name="Other School", adresse="Test", kommune="Test")
        self.course = Course.objects.create(
            start_date=date.today(),
            end_date=date.today(),
        )
        self.signup = CourseSignUp.objects.create(
            course=self.course,
            school=self.school,
            participant_name="Original Name",
            participant_email="original@test.dk",
        )

    def test_signup_edit_get(self):
        """Signup edit modal loads."""
        response = self.client.get(reverse("courses:signup-edit", kwargs={"pk": self.signup.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Original Name")

    def test_signup_edit_post(self):
        """Signup can be edited."""
        response = self.client.post(
            reverse("courses:signup-edit", kwargs={"pk": self.signup.pk}),
            {
                "participant_name": "New Name",
                "participant_email": "new@test.dk",
                "participant_phone": "12345678",
                "participant_title": "Teacher",
                "school": self.school2.pk,
                "is_underviser": True,
            },
        )
        self.signup.refresh_from_db()
        self.assertEqual(self.signup.participant_name, "New Name")
        self.assertEqual(self.signup.participant_email, "new@test.dk")
        self.assertEqual(self.signup.participant_phone, "12345678")
        self.assertEqual(self.signup.school, self.school2)
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/courses/tests.py::SignupEditViewTest -v`
Expected: FAIL with NoReverseMatch

**Step 3: Add SignupEditForm to forms.py**

Add to `apps/courses/forms.py`:

```python
class SignupEditForm(forms.ModelForm):
    class Meta:
        model = CourseSignUp
        fields = ["participant_name", "participant_email", "participant_phone", "participant_title", "school", "is_underviser"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["school"].queryset = School.objects.active()
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            "participant_name",
            Row(
                Column("participant_email", css_class="col-md-6"),
                Column("participant_phone", css_class="col-md-6"),
            ),
            "participant_title",
            "school",
            "is_underviser",
        )
```

**Step 4: Add SignupEditView to views.py**

Add to `apps/courses/views.py`:

```python
from .forms import CourseForm, CourseMaterialForm, PublicSignUpForm, SignupEditForm

@method_decorator(staff_required, name="dispatch")
class SignUpEditView(View):
    def get(self, request, pk):
        signup = get_object_or_404(CourseSignUp, pk=pk)
        form = SignupEditForm(instance=signup)
        return render(request, "courses/signup_edit_modal.html", {"signup": signup, "form": form})

    def post(self, request, pk):
        signup = get_object_or_404(CourseSignUp, pk=pk)
        form = SignupEditForm(request.POST, instance=signup)
        if form.is_valid():
            form.save()
            messages.success(request, "Tilmeldingen er blevet opdateret.")
            return JsonResponse({"success": True, "redirect": reverse("courses:detail", kwargs={"pk": signup.course.pk})})
        return render(request, "courses/signup_edit_modal.html", {"signup": signup, "form": form})
```

**Step 5: Create signup_edit_modal.html**

Create `apps/courses/templates/courses/signup_edit_modal.html`:

```html
{% load crispy_forms_tags %}
<div class="modal fade" id="signupEditModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <form method="post" action="{% url 'courses:signup-edit' signup.pk %}"
                  hx-post="{% url 'courses:signup-edit' signup.pk %}"
                  hx-target="#modal-container">
                {% csrf_token %}
                <div class="modal-header">
                    <h5 class="modal-title"><i class="bi bi-pencil me-2"></i>Rediger tilmelding</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    {% crispy form %}
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annuller</button>
                    <button type="submit" class="btn btn-primary">
                        <i class="bi bi-check-lg me-1"></i>Gem
                    </button>
                </div>
            </form>
        </div>
    </div>
</div>
<script>
    var modal = new bootstrap.Modal(document.getElementById('signupEditModal'));
    modal.show();
</script>
```

**Step 6: Add URL**

Add to `apps/courses/urls.py`:

```python
path('signups/<int:pk>/edit/', views.SignUpEditView.as_view(), name='signup-edit'),
```

**Step 7: Run test to verify it passes**

Run: `pytest apps/courses/tests.py::SignupEditViewTest -v`
Expected: PASS

**Step 8: Commit**

```bash
git add apps/courses/views.py apps/courses/forms.py apps/courses/urls.py apps/courses/templates/courses/signup_edit_modal.html apps/courses/tests.py
git commit -m "$(cat <<'EOF'
feat(courses): add signup edit view and modal

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: Update Bulk Import - New Format

**Files:**
- Modify: `apps/courses/views.py`
- Modify: `apps/courses/templates/courses/bulk_import_modal.html`
- Modify: `apps/courses/templates/courses/bulk_import_match.html`
- Test: `apps/courses/tests.py`

**Step 1: Write the failing test**

Add to `apps/courses/tests.py`:

```python
class BulkImportNewFormatTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123", is_staff=True)
        self.client.login(username="testuser", password="testpass123")
        self.school = School.objects.create(name="Test School", adresse="Test", kommune="Test")
        self.course = Course.objects.create(
            start_date=date.today(),
            end_date=date.today(),
        )

    def test_bulk_import_new_format(self):
        """Bulk import parses 6-column format (first, last, school, email, phone, is_underviser)."""
        data = "Anders\tJensen\tTest School\tanders@test.dk\t12345678\tja"
        response = self.client.post(
            reverse("courses:bulk-import", kwargs={"pk": self.course.pk}),
            {"data": data},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Anders Jensen")
        self.assertContains(response, "anders@test.dk")
        self.assertContains(response, "12345678")

    def test_bulk_import_name_concatenation(self):
        """Bulk import concatenates first and last name."""
        data = "Anders\t\tTest School\t\t\t"  # Empty last name
        response = self.client.post(
            reverse("courses:bulk-import", kwargs={"pk": self.course.pk}),
            {"data": data},
        )
        self.assertContains(response, "Anders")
        self.assertNotContains(response, "Anders ")  # No trailing space

    def test_bulk_import_is_underviser_parsing(self):
        """Bulk import parses is_underviser values."""
        data = "A\tB\tTest School\t\t\tnej\nC\tD\tTest School\t\t\tyes"
        response = self.client.post(
            reverse("courses:bulk-import", kwargs={"pk": self.course.pk}),
            {"data": data},
        )
        self.assertEqual(response.status_code, 200)
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/courses/tests.py::BulkImportNewFormatTest -v`
Expected: FAIL (current format doesn't support 6 columns)

**Step 3: Update BulkImportView in views.py**

Replace the post method of BulkImportView:

```python
def post(self, request, pk):
    from apps.schools.models import School

    course = get_object_or_404(Course, pk=pk)
    raw_data = request.POST.get("data", "")

    rows = []
    lines = raw_data.strip().split("\n")

    for line in lines:
        if not line.strip():
            continue

        # Split by tab (Excel default)
        parts = line.split("\t")

        # Expect 6 columns: first_name, last_name, school, email, phone, is_underviser
        first_name = parts[0].strip() if len(parts) > 0 else ""
        last_name = parts[1].strip() if len(parts) > 1 else ""
        school_name = parts[2].strip() if len(parts) > 2 else ""
        email = parts[3].strip() if len(parts) > 3 else ""
        phone = parts[4].strip() if len(parts) > 4 else ""
        is_underviser_raw = parts[5].strip().lower() if len(parts) > 5 else ""

        # Concatenate name
        name_parts = [p for p in [first_name, last_name] if p]
        name = " ".join(name_parts)

        if not name or not school_name:
            continue

        # Parse is_underviser
        if is_underviser_raw in ["nej", "no", "0", "false"]:
            is_underviser = False
        else:
            is_underviser = True  # Default to True

        # Find matching schools
        matches = self._find_school_matches(school_name)

        rows.append({
            "index": len(rows),
            "name": name,
            "school_name": school_name,
            "email": email,
            "phone": phone,
            "is_underviser": is_underviser,
            "matches": matches,
            "exact_match": matches[0] if matches and matches[0].name.lower() == school_name.lower() else None,
        })

    if not rows:
        messages.error(request, "Ingen gyldige rækker fundet. Forventet format: Fornavn, Efternavn, Skole, Email, Telefon, Underviser (tab-separeret)")
        return render(request, "courses/bulk_import_modal.html", {"course": course})

    all_schools = School.objects.active().order_by("name")

    return render(
        request,
        "courses/bulk_import_match.html",
        {
            "course": course,
            "rows": rows,
            "all_schools": all_schools,
        },
    )
```

**Step 4: Update bulk_import_modal.html**

Update `apps/courses/templates/courses/bulk_import_modal.html`:

```html
<div class="modal fade" id="bulkImportModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <form method="post" action="{% url 'courses:bulk-import' course.pk %}">
                {% csrf_token %}
                <div class="modal-header">
                    <h5 class="modal-title"><i class="bi bi-upload me-2"></i>Bulk import tilmeldinger</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <p class="text-muted">
                        Indsæt data fra Excel (tab-separeret). Forventet format:
                    </p>
                    <div class="alert alert-info small">
                        <strong>Kolonne 1:</strong> Fornavn<br>
                        <strong>Kolonne 2:</strong> Efternavn<br>
                        <strong>Kolonne 3:</strong> Skolens navn<br>
                        <strong>Kolonne 4:</strong> Email (valgfri)<br>
                        <strong>Kolonne 5:</strong> Telefon (valgfri)<br>
                        <strong>Kolonne 6:</strong> Er underviser - ja/nej (valgfri, standard: ja)
                    </div>
                    <div class="mb-3">
                        <label for="data" class="form-label">Data fra Excel</label>
                        <textarea name="data" id="data" class="form-control font-monospace" rows="10"
                                  placeholder="Anders&#9;Jensen&#9;Eksempel Skole&#9;anders@eksempel.dk&#9;12345678&#9;ja
Maria&#9;Nielsen&#9;Anden Skole&#9;maria@anden.dk&#9;87654321&#9;nej"></textarea>
                    </div>
                    <p class="small text-muted mb-0">
                        <i class="bi bi-info-circle me-1"></i>
                        Skoler vil blive matchet i næste trin. Du kan vælge den korrekte skole hvis navnet ikke matcher præcist.
                    </p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annuller</button>
                    <button type="submit" class="btn btn-primary">
                        <i class="bi bi-arrow-right me-1"></i>Næste
                    </button>
                </div>
            </form>
        </div>
    </div>
</div>
```

**Step 5: Update bulk_import_match.html**

Update `apps/courses/templates/courses/bulk_import_match.html` to include phone and is_underviser columns:

```html
{% extends 'core/base.html' %}

{% block title %}Bulk Import - {{ course.display_name }} - Basal{% endblock %}

{% block content %}
<nav aria-label="breadcrumb" class="mb-3">
    <ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="{% url 'courses:list' %}">Kurser</a></li>
        <li class="breadcrumb-item"><a href="{% url 'courses:detail' course.pk %}">{{ course.display_name }}</a></li>
        <li class="breadcrumb-item active">Bulk Import</li>
    </ol>
</nav>

<div class="d-flex justify-content-between align-items-center mb-4">
    <h1><i class="bi bi-upload me-2"></i>Vælg skoler</h1>
</div>

<div class="alert alert-info">
    <i class="bi bi-info-circle me-2"></i>
    Vælg den korrekte skole for hver deltager. Du kan også justere telefon og underviser-status.
</div>

<form method="post" action="{% url 'courses:bulk-import-confirm' course.pk %}">
    {% csrf_token %}
    <input type="hidden" name="count" value="{{ rows|length }}">

    <div class="card">
        <div class="table-responsive">
            <table class="table table-hover mb-0">
                <thead class="table-light">
                    <tr>
                        <th style="width: 18%">Deltager</th>
                        <th style="width: 15%">Indtastet skole</th>
                        <th style="width: 25%">Vælg skole</th>
                        <th style="width: 15%">Email</th>
                        <th style="width: 12%">Telefon</th>
                        <th style="width: 10%">Underviser</th>
                    </tr>
                </thead>
                <tbody>
                    {% for row in rows %}
                    <tr>
                        <td>
                            <strong>{{ row.name }}</strong>
                            <input type="hidden" name="name_{{ row.index }}" value="{{ row.name }}">
                        </td>
                        <td>
                            <span class="text-muted">{{ row.school_name }}</span>
                        </td>
                        <td>
                            <select name="school_{{ row.index }}" class="form-select form-select-sm">
                                <option value="skip">-- Spring over --</option>
                                {% if row.exact_match %}
                                <option value="{{ row.exact_match.pk }}" selected>
                                    {{ row.exact_match.name }} ({{ row.exact_match.kommune }})
                                </option>
                                {% else %}
                                    {% if row.matches %}
                                    <optgroup label="Forslag">
                                        {% for match in row.matches %}
                                        <option value="{{ match.pk }}" {% if forloop.first %}selected{% endif %}>
                                            {{ match.name }} ({{ match.kommune }})
                                        </option>
                                        {% endfor %}
                                    </optgroup>
                                    {% endif %}
                                {% endif %}
                                <optgroup label="Alle skoler">
                                    {% for school in all_schools %}
                                    <option value="{{ school.pk }}">{{ school.name }} ({{ school.kommune }})</option>
                                    {% endfor %}
                                </optgroup>
                            </select>
                        </td>
                        <td>
                            <input type="email" name="email_{{ row.index }}" value="{{ row.email }}" class="form-control form-control-sm" placeholder="-">
                        </td>
                        <td>
                            <input type="text" name="phone_{{ row.index }}" value="{{ row.phone }}" class="form-control form-control-sm" placeholder="-">
                        </td>
                        <td class="text-center">
                            <input type="checkbox" name="is_underviser_{{ row.index }}" class="form-check-input" {% if row.is_underviser %}checked{% endif %}>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <div class="mt-4 d-flex justify-content-between">
        <a href="{% url 'courses:detail' course.pk %}" class="btn btn-outline-secondary">
            <i class="bi bi-x-lg me-1"></i>Annuller
        </a>
        <button type="submit" class="btn btn-success">
            <i class="bi bi-check-lg me-1"></i>Importér {{ rows|length }} tilmelding{{ rows|length|pluralize:"er" }}
        </button>
    </div>
</form>
{% endblock %}
```

**Step 6: Update BulkImportConfirmView**

Update BulkImportConfirmView post method to handle phone and is_underviser:

```python
def post(self, request, pk):
    from apps.schools.models import School

    course = get_object_or_404(Course, pk=pk)

    count = int(request.POST.get("count", 0))
    created = 0
    skipped = 0
    errors = []

    for i in range(count):
        school_id = request.POST.get(f"school_{i}")
        name = request.POST.get(f"name_{i}")
        email = request.POST.get(f"email_{i}", "")
        phone = request.POST.get(f"phone_{i}", "")
        is_underviser = request.POST.get(f"is_underviser_{i}") == "on"

        if not school_id or school_id == "skip":
            skipped += 1
            continue

        try:
            school = School.objects.get(pk=school_id)

            if CourseSignUp.objects.filter(course=course, school=school, participant_name=name).exists():
                errors.append(f"{name} ({school.name}) er allerede tilmeldt")
                continue

            CourseSignUp.objects.create(
                course=course,
                school=school,
                participant_name=name,
                participant_email=email,
                participant_phone=phone,
                is_underviser=is_underviser,
            )
            created += 1

        except School.DoesNotExist:
            errors.append(f"Skole ikke fundet for {name}")
        except Exception as e:
            errors.append(f"Fejl ved oprettelse af {name}: {str(e)}")

    # Build result message (same as before)
    msg_parts = []
    if created:
        msg_parts.append(f'{created} tilmelding{"er" if created != 1 else ""} oprettet')
    if skipped:
        msg_parts.append(f"{skipped} sprunget over")
    if errors:
        msg_parts.append(f"{len(errors)} fejl")

    if created:
        messages.success(request, ". ".join(msg_parts) + ".")
    elif errors:
        messages.error(request, ". ".join(msg_parts) + ".")
    else:
        messages.warning(request, "Ingen tilmeldinger oprettet.")

    if errors:
        for error in errors[:5]:
            messages.warning(request, error)

    return redirect("courses:detail", pk=course.pk)
```

**Step 7: Run test to verify it passes**

Run: `pytest apps/courses/tests.py::BulkImportNewFormatTest -v`
Expected: PASS

**Step 8: Commit**

```bash
git add apps/courses/views.py apps/courses/templates/courses/bulk_import_modal.html apps/courses/templates/courses/bulk_import_match.html apps/courses/tests.py
git commit -m "$(cat <<'EOF'
feat(courses): update bulk import to 6-column format

Format: first_name, last_name, school, email, phone, is_underviser

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: Update Course List and Other Templates

**Files:**
- Modify: `apps/courses/templates/courses/course_list.html`
- Modify: `apps/courses/templates/courses/rollcall.html`

**Step 1: Update course_list.html**

Update any references to `course.title` to use `course.display_name`.

**Step 2: Update rollcall.html**

Update breadcrumb and title to use `course.display_name` and add phone column.

**Step 3: Run all tests**

Run: `pytest apps/courses/ -v`
Expected: All tests pass

**Step 4: Commit**

```bash
git add apps/courses/templates/
git commit -m "$(cat <<'EOF'
feat(courses): update remaining templates to use display_name

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 14: Final Test Run and Cleanup

**Step 1: Run full test suite**

Run: `pytest -v`
Expected: All tests pass

**Step 2: Manual verification**

1. Create a new course - verify form works with location/instructor dropdowns
2. Edit a course - verify existing data loads correctly
3. View course detail - verify display_name shows correctly
4. Edit a signup - verify modal works
5. Bulk import - verify 6-column format works

**Step 3: Commit any final fixes**

```bash
git add .
git commit -m "$(cat <<'EOF'
chore(courses): test fixes and cleanup

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Summary of Files Changed

| File | Action |
|------|--------|
| `apps/courses/models.py` | Add Instructor, Location models; update Course |
| `apps/courses/admin.py` | Register Instructor, Location |
| `apps/courses/forms.py` | Update CourseForm, add SignupEditForm |
| `apps/courses/views.py` | Add SignUpEditView, update BulkImportView |
| `apps/courses/urls.py` | Add signup-edit route |
| `apps/courses/tests.py` | Add tests for new functionality |
| `apps/courses/templates/courses/course_form.html` | Add JS for "add new" options |
| `apps/courses/templates/courses/course_detail.html` | Update display, add phone/edit |
| `apps/courses/templates/courses/signup_edit_modal.html` | New file |
| `apps/courses/templates/courses/bulk_import_modal.html` | Update format instructions |
| `apps/courses/templates/courses/bulk_import_match.html` | Add phone/is_underviser columns |
| `apps/courses/templates/courses/course_list.html` | Use display_name |
| `apps/courses/templates/courses/rollcall.html` | Use display_name, add phone |
| `apps/courses/migrations/` | Multiple new migrations |
