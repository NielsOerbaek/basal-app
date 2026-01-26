# Improved Course Page Design

## Overview

Improvements to the course management system including auto-generated course names, managed instructor/location lists, signup editing, and enhanced bulk import.

## Data Model Changes

### New Models

#### Instructor
```python
class Instructor(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
```

#### Location
```python
class Location(models.Model):
    name = models.CharField(max_length=255)
    street_address = models.CharField(max_length=255, blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    municipality = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

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

### Course Model Changes

**Remove:**
- `title` field
- `undervisere` CharField
- `location` CharField

**Add:**
- `location` ForeignKey to Location (nullable, on_delete=SET_NULL)
- `instructors` ManyToManyField to Instructor (blank=True)

**New property:**
```python
@property
def display_name(self):
    """Auto-generated course name with dates."""
    if self.start_date == self.end_date:
        date_str = self.start_date.strftime("%-d. %b %Y")
    else:
        start_str = self.start_date.strftime("%-d. %b")
        end_str = self.end_date.strftime("%-d. %b %Y")
        date_str = f"{start_str} - {end_str}"
    return f"Kompetenceudviklingskursus, {date_str}"
```

**Updated `__str__`:**
```python
def __str__(self):
    return self.display_name
```

## Course Form

### Layout
```
Startdato:        [date picker]
Slutdato:         [date picker]
Sted:             [dropdown: existing locations + "Tilføj ny..."]
                  (if new: Name, Street, Postal, Municipality fields appear)
Underviser 1:     [dropdown + "Tilføj ny..."] (required)
Underviser 2:     [dropdown + "Tilføj ny..."] (optional)
Underviser 3:     [dropdown + "Tilføj ny..."] (optional)
Kapacitet:        [number]
Kommentar:        [textarea]
Offentliggjort:   [checkbox]
```

### Behavior
- Location dropdown includes all existing locations plus "Tilføj ny..." option
- Selecting "Tilføj ny..." reveals inline fields for name, street, postal code, municipality
- New locations are saved to the database and selected automatically
- Same pattern for instructor dropdowns
- New instructors are saved to the database for future reuse

## Course Detail Page

### Header
Display auto-generated name instead of title:
- Single day: "Kompetenceudviklingskursus, 15. jan 2026"
- Multi-day: "Kompetenceudviklingskursus, 15. jan - 17. jan 2026"

### Course Info Card
- Remove "Dato" row (date is in the title)
- "Sted" shows full location address: "Basal Hovedkontor, Vesterbrogade 123, 1620 København V"
- "Undervisere" shows comma-separated list of instructor names, or "-" if none

### Participants Table
Updated columns:
| Navn | E-mail | Telefon | Titel | Underviser | Skole | Fremmøde | (actions) |

- Add phone column after email
- Add edit button (pencil icon) before delete button on each row

## Signup Editing

### Edit Modal
New modal form accessible via pencil icon on each signup row.

**Fields:**
- Participant name (text, required)
- Email (email, optional)
- Phone (text, optional)
- Title (text, optional)
- School (dropdown, required)
- Is underviser (checkbox)

**Behavior:**
- Opens via HTMX modal
- Save updates the row without full page reload
- Cancel closes modal without changes

## Bulk Import

### Format
6 columns, tab-separated, no header row:

```
Fornavn   Efternavn   Skole           Email               Telefon         Underviser
```

1. First name (required)
2. Last name (optional)
3. School name (required)
4. Email (optional)
5. Phone (optional)
6. Is underviser (optional, defaults to true)

### Name Handling
- First name + last name concatenated with space
- If last name empty: just first name
- If first name empty: just last name

### Is Underviser Values
Accepts: "ja"/"nej", "yes"/"no", "1"/"0", empty (defaults to true)

### Process Flow
1. User pastes data into text area
2. System parses and matches schools (existing fuzzy matching)
3. Matching screen shows all fields including phone and is_underviser with override options
4. Confirm creates signups

## Admin

Register both new models for direct list management:

```python
@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ["name", "created_at"]
    search_fields = ["name"]

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ["name", "street_address", "postal_code", "municipality", "created_at"]
    search_fields = ["name", "street_address", "municipality"]
```

## Database Migration Strategy

### Step 1: Create New Models
- Create `Instructor` model
- Create `Location` model

### Step 2: Add New Fields to Course
- Add `location_fk` (ForeignKey to Location, nullable)
- Add `instructors` (ManyToMany to Instructor)

### Step 3: Data Migration
```python
def migrate_course_data(apps, schema_editor):
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
        course.location_fk = location
        course.save()
```

### Step 4: Remove Old Fields
- Remove `title` from Course
- Remove `undervisere` CharField from Course
- Remove `location` CharField from Course
- Rename `location_fk` to `location`

## Files to Modify

### Models
- `apps/courses/models.py` - Add Instructor, Location models; update Course model

### Forms
- `apps/courses/forms.py` - Update CourseForm, add SignupEditForm

### Views
- `apps/courses/views.py` - Update CourseCreateView, CourseUpdateView; add SignupEditView; update BulkImportView

### Templates
- `apps/courses/templates/courses/course_form.html` - New layout with instructor/location dropdowns
- `apps/courses/templates/courses/course_detail.html` - Updated display, phone column, edit button
- `apps/courses/templates/courses/signup_edit_modal.html` - New template
- `apps/courses/templates/courses/bulk_import_modal.html` - Updated instructions
- `apps/courses/templates/courses/bulk_import_match.html` - Add phone, is_underviser columns

### Admin
- `apps/courses/admin.py` - Register Instructor, Location

### URLs
- `apps/courses/urls.py` - Add signup edit route

## Testing

- Model tests for Instructor, Location
- Course display_name property tests
- Form tests for instructor/location creation
- Signup edit view tests
- Bulk import tests with new format
- Migration tests
