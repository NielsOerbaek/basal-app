# School Files and Public Page Enhancements

## Overview

Add two features:
1. Internal file uploads per school (staff-only)
2. Enhanced public school page showing course attendance and materials

## 1. Internal School Files

### Model: `SchoolFile`

Location: `apps/schools/models.py`

```python
class SchoolFile(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='school_files/%Y/%m/')
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.file.name
```

### Staff UI

On school detail page (`/schools/<pk>/`), add "Filer" section:
- List of files: filename (download link), description, upload date, uploaded by
- "Tilføj fil" button
- Delete button per file with confirmation

Routes:
- `POST /schools/<pk>/file/add/` - upload file
- `POST /schools/file/<pk>/delete/` - delete file

Use HTMX for add/delete without page reload.

### Audit

Register in `apps/audit/apps.py`:
```python
register_for_audit(SchoolFile, AuditCfg(
    excluded_fields=['id', 'uploaded_at'],
    get_school=lambda instance: instance.school,
))
```

## 2. Public School Page Enhancements

Location: `/school/<token>/`

### Section: Kontaktpersoner

Existing `Person` records with course attendance:

```
Anders Jensen
Koordinator, Klasselærer
anders@skole.dk | 12 34 56 78
  └─ Uddannet på Kompetenceudviklingskursus, 1. feb - 3. feb 2026, København
  └─ Tilmeldt Kompetenceudviklingskursus, 15. mar - 17. mar 2026, Aarhus
```

Logic:
- For each Person, match email (case-insensitive) to CourseSignUp.participant_email
- Show attendance status line per matching signup
- Sort courses chronologically by start_date

Status text mapping:
- `attendance_status = 'present'` → "Uddannet på [course title]"
- `attendance_status = 'absent'` → "Mødte ikke op til [course title]"
- `attendance_status = 'unmarked'` → "Tilmeldt [course title]"

### Section: Kursusdeltagere

CourseSignUp participants not already shown as contacts:

```
Maria Hansen
maria@skole.dk
  └─ Tilmeldt Kompetenceudviklingskursus, 15. mar - 17. mar 2026, Aarhus

Peter Olsen
peter@skole.dk
  └─ Uddannet på Kompetenceudviklingskursus, 1. feb - 3. feb 2026, København
```

Logic:
- Get all CourseSignUp records for this school
- Exclude signups where participant_email matches a Person's email
- Group remaining by participant_email
- Show name, email, and attendance lines per course
- Sort courses chronologically by start_date

### Section: Kursusmaterialer

Download links for course materials:

```
Kursusmaterialer

Kompetenceudviklingskursus, 1. feb - 3. feb 2026, København
  📄 Kursusplan.pdf
  📄 Slides dag 1.pdf

Kompetenceudviklingskursus, 15. mar - 17. mar 2026, Aarhus
  📄 Kursusplan.pdf
```

Logic:
- Find all courses where school has at least one CourseSignUp
- Filter to courses that have CourseMaterial files
- Sort courses newest first (by start_date descending)
- List each course's materials as download links

## Files to Modify

| File | Changes |
|------|---------|
| `apps/schools/models.py` | Add SchoolFile model |
| `apps/schools/views.py` | Add SchoolFileCreateView, SchoolFileDeleteView |
| `apps/schools/urls.py` | Add routes for file upload/delete |
| `apps/schools/templates/schools/school_detail.html` | Add "Filer" section |
| `apps/schools/forms.py` | Add SchoolFileForm |
| `apps/signups/views.py` | Update school_public_view with course data |
| `apps/signups/templates/signups/school_public.html` | Add kursusdeltagere and kursusmaterialer sections, add attendance to kontaktpersoner |
| `apps/audit/apps.py` | Register SchoolFile for auditing |

## Migration

One new migration for SchoolFile model.
