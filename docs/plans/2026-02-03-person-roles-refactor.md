# Person Roles Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace `is_primary` + `role` dropdown with two independent booleans: `is_koordinator` and `is_oekonomisk_ansvarlig`.

**Architecture:** Three-migration approach (add fields → migrate data → remove old fields) ensures safe rollback. UI changes update form and templates to show role chips.

**Tech Stack:** Django 5.x, crispy-forms, Bootstrap 5

---

## Task 1: Add New Boolean Fields

**Files:**
- Modify: `apps/schools/models.py:367-403`
- Create: `apps/schools/migrations/0025_add_koordinator_fields.py`

**Step 1: Add new fields to Person model**

In `apps/schools/models.py`, add after line 379 (`is_primary` field):

```python
    is_koordinator = models.BooleanField(default=False, verbose_name="Koordinator")
    is_oekonomisk_ansvarlig = models.BooleanField(default=False, verbose_name="Økonomisk ansvarlig")
```

**Step 2: Add roles property**

Add after the `display_role` property (around line 402):

```python
    @property
    def roles(self):
        """Return list of role labels for chip display."""
        result = []
        if self.is_koordinator:
            result.append("Koordinator")
        if self.is_oekonomisk_ansvarlig:
            result.append("Økonomisk ansvarlig")
        return result
```

**Step 3: Create migration**

Run: `python manage.py makemigrations schools --name add_koordinator_fields`

**Step 4: Apply migration**

Run: `python manage.py migrate`

**Step 5: Verify**

Run: `python manage.py shell -c "from apps.schools.models import Person; p = Person(); print(p.is_koordinator, p.is_oekonomisk_ansvarlig)"`

Expected: `False False`

**Step 6: Commit**

```bash
git add apps/schools/models.py apps/schools/migrations/0025_add_koordinator_fields.py
git commit -m "feat(schools): add is_koordinator and is_oekonomisk_ansvarlig fields to Person"
```

---

## Task 2: Write Data Migration

**Files:**
- Create: `apps/schools/migrations/0026_migrate_person_roles.py`

**Step 1: Create empty migration**

Run: `python manage.py makemigrations schools --empty --name migrate_person_roles`

**Step 2: Write migration code**

Replace contents of `apps/schools/migrations/0026_migrate_person_roles.py`:

```python
from django.db import migrations


def migrate_person_roles(apps, schema_editor):
    Person = apps.get_model('schools', 'Person')

    for person in Person.objects.select_related('school').all():
        school_enrolled = (
            person.school.enrolled_at is not None
            and (person.school.opted_out_at is None or person.school.opted_out_at > person.school.enrolled_at)
        )

        # Migrate is_primary for enrolled schools only
        if person.is_primary and school_enrolled:
            person.is_koordinator = True

        # Migrate existing role values (all schools)
        if person.role == 'koordinator':
            person.is_koordinator = True
        elif person.role == 'oekonomisk_ansvarlig':
            person.is_oekonomisk_ansvarlig = True

        person.save(update_fields=['is_koordinator', 'is_oekonomisk_ansvarlig'])


def reverse_migrate(apps, schema_editor):
    Person = apps.get_model('schools', 'Person')

    for person in Person.objects.all():
        if person.is_koordinator:
            person.role = 'koordinator'
            person.is_primary = True
        elif person.is_oekonomisk_ansvarlig:
            person.role = 'oekonomisk_ansvarlig'
        else:
            person.role = 'andet'
        person.save(update_fields=['role', 'is_primary'])


class Migration(migrations.Migration):

    dependencies = [
        ('schools', '0025_add_koordinator_fields'),
    ]

    operations = [
        migrations.RunPython(migrate_person_roles, reverse_migrate),
    ]
```

**Step 3: Apply migration**

Run: `python manage.py migrate`

**Step 4: Verify migration**

Run: `python manage.py shell -c "from apps.schools.models import Person; print([(p.name, p.is_koordinator, p.is_oekonomisk_ansvarlig) for p in Person.objects.all()[:5]])"`

**Step 5: Commit**

```bash
git add apps/schools/migrations/0026_migrate_person_roles.py
git commit -m "feat(schools): migrate existing role data to new boolean fields"
```

---

## Task 3: Update Tests

**Files:**
- Modify: `apps/schools/tests.py`

**Step 1: Update test_person_ordering**

Find `test_person_ordering` (around line 184) and replace with:

```python
    def test_person_ordering(self):
        """Persons are ordered by is_koordinator (desc), is_oekonomisk_ansvarlig (desc), then name."""
        person1 = Person.objects.create(school=self.school, name="Zach", is_koordinator=False)
        person2 = Person.objects.create(school=self.school, name="Alice", is_koordinator=True)
        person3 = Person.objects.create(school=self.school, name="Bob", is_oekonomisk_ansvarlig=True)
        people = list(self.school.people.all())
        self.assertEqual(people[0], person2)  # Alice (koordinator)
        self.assertEqual(people[1], person3)  # Bob (oekonomisk_ansvarlig)
        self.assertEqual(people[2], person1)  # Zach (neither)
```

**Step 2: Remove obsolete tests**

Delete these test methods:
- `test_display_role_standard` (around line 169)
- `test_display_role_other` (around line 174)

**Step 3: Add new tests**

Add after `test_person_ordering`:

```python
    def test_person_can_have_both_roles(self):
        """Person can be both koordinator and oekonomisk_ansvarlig."""
        person = Person.objects.create(
            school=self.school,
            name="Both Roles",
            is_koordinator=True,
            is_oekonomisk_ansvarlig=True,
        )
        self.assertTrue(person.is_koordinator)
        self.assertTrue(person.is_oekonomisk_ansvarlig)

    def test_person_roles_property(self):
        """roles property returns correct labels."""
        person1 = Person.objects.create(school=self.school, name="P1", is_koordinator=True)
        person2 = Person.objects.create(school=self.school, name="P2", is_oekonomisk_ansvarlig=True)
        person3 = Person.objects.create(school=self.school, name="P3", is_koordinator=True, is_oekonomisk_ansvarlig=True)
        person4 = Person.objects.create(school=self.school, name="P4")

        self.assertEqual(person1.roles, ["Koordinator"])
        self.assertEqual(person2.roles, ["Økonomisk ansvarlig"])
        self.assertEqual(person3.roles, ["Koordinator", "Økonomisk ansvarlig"])
        self.assertEqual(person4.roles, [])
```

**Step 4: Run tests to verify**

Run: `python manage.py test apps.schools.tests.PersonModelTest -v 2`

Expected: All tests pass

**Step 5: Commit**

```bash
git add apps/schools/tests.py
git commit -m "test(schools): update person tests for new role fields"
```

---

## Task 4: Update Person Form

**Files:**
- Modify: `apps/schools/forms.py:85-113`

**Step 1: Update PersonForm fields**

Replace the `PersonForm` class (lines 85-113) with:

```python
class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = ["name", "titel", "titel_other", "phone", "email", "comment", "is_koordinator", "is_oekonomisk_ansvarlig"]
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("name", css_class="col-md-6"),
                Column("titel", css_class="col-md-3"),
                Column("titel_other", css_class="col-md-3"),
            ),
            Row(
                Column("phone", css_class="col-md-6"),
                Column("email", css_class="col-md-6"),
            ),
            "comment",
            Row(
                Column("is_koordinator", css_class="col-md-6"),
                Column("is_oekonomisk_ansvarlig", css_class="col-md-6"),
            ),
            Submit("submit", "Gem person", css_class="btn btn-primary"),
        )
```

**Step 2: Run tests**

Run: `python manage.py test apps.schools.tests.PersonViewTest -v 2`

Expected: All tests pass

**Step 3: Commit**

```bash
git add apps/schools/forms.py
git commit -m "feat(schools): update PersonForm with koordinator checkboxes"
```

---

## Task 5: Update School Detail Template

**Files:**
- Modify: `apps/schools/templates/schools/school_detail.html:184-208`

**Step 1: Update person display**

Replace lines 188-191 (the person name/role display) with:

```html
                            <div class="mb-1">
                                <strong>{{ person.name }}</strong>{% if person.display_titel %}, {{ person.display_titel|lower }}{% endif %}
                                {% for role in person.roles %}
                                <span class="badge {% if role == 'Koordinator' %}bg-primary{% else %}bg-secondary{% endif %} ms-1">{{ role }}</span>
                                {% endfor %}
                            </div>
```

**Step 2: Verify in browser**

Run: `python manage.py runserver`

Visit: `http://localhost:8000/schools/` and click on a school with people

Expected: People show chips for their roles instead of "primær kontakt"

**Step 3: Commit**

```bash
git add apps/schools/templates/schools/school_detail.html
git commit -m "feat(schools): show role chips in person list"
```

---

## Task 6: Update Public School Template

**Files:**
- Modify: `apps/schools/templates/schools/school_public.html:147-158`

**Step 1: Update person display**

Find lines 150-152 and replace with:

```html
                            <strong>{{ item.person.name }}</strong>
                            {% for role in item.person.roles %}
                            <span class="badge {% if role == 'Koordinator' %}bg-primary{% else %}bg-secondary{% endif %} ms-1">{{ role }}</span>
                            {% endfor %}
```

**Step 2: Verify in browser**

Visit a school's public page (use the signup_token URL)

Expected: People show role chips

**Step 3: Commit**

```bash
git add apps/schools/templates/schools/school_public.html
git commit -m "feat(schools): show role chips on public school page"
```

---

## Task 7: Remove Old Fields

**Files:**
- Modify: `apps/schools/models.py`
- Create: `apps/schools/migrations/0027_remove_old_person_fields.py`

**Step 1: Update model ordering**

In `apps/schools/models.py`, find the `Person` class Meta (around line 382) and change ordering:

```python
    class Meta:
        ordering = ["-is_koordinator", "-is_oekonomisk_ansvarlig", "name"]
```

**Step 2: Remove old fields from model**

Remove these lines from `Person` model:
- `role = models.CharField(...)` (line 372-374)
- `role_other = models.CharField(...)` (line 375)
- `is_primary = models.BooleanField(...)` (line 379)

**Step 3: Remove display_role property**

Remove the `display_role` property (around line 398-402)

**Step 4: Update __str__ method**

Change `__str__` (around line 387) from:
```python
    def __str__(self):
        return f"{self.name} ({self.display_role})"
```

To:
```python
    def __str__(self):
        roles = ", ".join(self.roles) if self.roles else "Ingen rolle"
        return f"{self.name} ({roles})"
```

**Step 5: Remove PersonRole class**

Delete the `PersonRole` class at the top of the file (lines 7-10)

**Step 6: Create migration**

Run: `python manage.py makemigrations schools --name remove_old_person_fields`

**Step 7: Apply migration**

Run: `python manage.py migrate`

**Step 8: Run all tests**

Run: `python manage.py test apps.schools -v 2`

Expected: All tests pass

**Step 9: Commit**

```bash
git add apps/schools/models.py apps/schools/migrations/0027_remove_old_person_fields.py
git commit -m "feat(schools): remove is_primary, role, role_other fields from Person"
```

---

## Task 8: Update Remaining Tests

**Files:**
- Modify: `apps/schools/tests.py`

**Step 1: Find and update tests using old fields**

Search for `PersonRole` and `is_primary` in tests and update:

- Replace `PersonRole.KOORDINATOR` with `is_koordinator=True`
- Replace `is_primary=True` with `is_koordinator=True`
- Remove any imports of `PersonRole`

**Step 2: Run full test suite**

Run: `python manage.py test apps.schools -v 2`

Expected: All 151+ tests pass

**Step 3: Commit**

```bash
git add apps/schools/tests.py
git commit -m "test(schools): update all tests for new role fields"
```

---

## Task 9: Final Verification

**Step 1: Run full test suite**

Run: `python manage.py test apps.schools -v 2`

Expected: All tests pass

**Step 2: Manual verification**

1. Visit school list, click a school
2. Verify people show role chips (Koordinator in blue, Økonomisk ansvarlig in gray)
3. Click "Tilføj person", verify two checkboxes appear
4. Create a person with both roles checked
5. Verify both chips display
6. Visit public school page, verify chips display there too

**Step 3: Final commit (if any cleanup needed)**

```bash
git status
# If changes: git add . && git commit -m "chore: final cleanup"
```
