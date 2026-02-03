# Person Roles Refactor Design

## Overview

Replace the single "Primær kontakt" checkbox and "Role" dropdown with two independent boolean fields: `is_koordinator` and `is_oekonomisk_ansvarlig`. A person can have both roles, one, or neither.

## Data Model Changes

**Person model (apps/schools/models.py)**

Remove:
- `is_primary` (BooleanField)
- `role` (CharField with choices)
- `role_other` (CharField)
- `PersonRole` class

Add:
- `is_koordinator` (BooleanField, default=False, verbose_name="Koordinator")
- `is_oekonomisk_ansvarlig` (BooleanField, default=False, verbose_name="Økonomisk ansvarlig")

**Ordering:**
`["-is_koordinator", "-is_oekonomisk_ansvarlig", "name"]`

**Helper property:**
```python
@property
def roles(self):
    result = []
    if self.is_koordinator:
        result.append("Koordinator")
    if self.is_oekonomisk_ansvarlig:
        result.append("Økonomisk ansvarlig")
    return result
```

## Migration Strategy

**Migration 1: Add new fields**
- Add `is_koordinator` (default=False)
- Add `is_oekonomisk_ansvarlig` (default=False)

**Migration 2: Data migration**
```python
def migrate_person_roles(apps, schema_editor):
    Person = apps.get_model('schools', 'Person')

    for person in Person.objects.all():
        school_enrolled = person.school.is_enrolled

        # Migrate is_primary for enrolled schools only
        if person.is_primary and school_enrolled:
            person.is_koordinator = True

        # Migrate existing role values (all schools)
        if person.role == 'koordinator':
            person.is_koordinator = True
        elif person.role == 'oekonomisk_ansvarlig':
            person.is_oekonomisk_ansvarlig = True

        person.save()
```

**Migration 3: Remove old fields**
- Remove `is_primary`
- Remove `role`
- Remove `role_other`

## UI Changes

**Person form (apps/schools/forms.py)**
- Remove: `role`, `role_other`, `is_primary`
- Add: `is_koordinator`, `is_oekonomisk_ansvarlig` as checkboxes in a row

**Contact person list (school_detail.html)**
Display chips next to person names:
```html
<span class="badge bg-primary">Koordinator</span>
<span class="badge bg-secondary">Økonomisk ansvarlig</span>
```

**Public school page (school_public.html)**
Same chip display for contact persons.

## Test Updates

**Update:**
- `test_person_ordering` - Test new ordering
- Remove `test_display_role_standard`, `test_display_role_other`
- Update tests using `PersonRole` or `is_primary`

**Add:**
- `test_person_can_have_both_roles`
- `test_person_roles_property`
- `test_person_form_has_checkboxes`
