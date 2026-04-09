# Kommune-Affiliated Course Participants Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `CourseSignUp` rows be affiliated with a `Kommune` as a first-class relation (not free text), and surface those participants on the kommune detail page.

**Architecture:** Add nullable `kommune` FK to `CourseSignUp`, enforce XOR over `{school, kommune, other_organization}` via form `clean()` + a DB `CheckConstraint`. Seed all 98 Danish kommuner into the existing `Kommune` table (currently populated lazily only when billing is enabled). Backfill existing free-text matches into the new FK, fix one known typo (`Vesthimmerland` → `Vesthimmerlands`). Extract the school detail page's participant list into a reusable partial used by both school detail and the new "Deltagere fra kommunen" section on kommune detail.

**Tech Stack:** Django 5, crispy-forms, Bootstrap 5, pytest-django.

**Spec:** `docs/superpowers/specs/2026-04-09-kommune-course-participants-design.md`

---

## File Structure

**Create:**
- `apps/schools/kommuner.py` — canonical list of 98 kommune names (single source of truth, used by migration + form)
- `apps/schools/migrations/0038_fix_vesthimmerland_typo.py` — data migration, typo fix on `School.kommune`
- `apps/schools/migrations/0039_seed_all_kommuner.py` — data migration, seed `Kommune` table
- `apps/courses/migrations/0019_coursesignup_kommune.py` — schema: add `kommune` FK
- `apps/courses/migrations/0020_backfill_coursesignup_kommune.py` — data: move matching `other_organization` → `kommune` FK
- `apps/courses/migrations/0021_coursesignup_affiliation_xor.py` — add `CheckConstraint`
- `apps/schools/templates/schools/_participant_list.html` — reusable participant list partial

**Modify:**
- `apps/courses/models.py` — add FK, update `clean()`, `__str__`, `organization_name`, add constraint in `Meta`
- `apps/courses/forms.py` — `CourseSignUpForm`: radio toggle + kommune field + updated `clean()`
- `apps/schools/templates/schools/school_detail.html` — replace inline participant list with `{% include %}`
- `apps/schools/templates/schools/kommune_detail.html` — add "Deltagere fra kommunen" section + stat line
- `apps/schools/views.py::KommuneDetailView.get_context_data` — add `kursusdeltagere` + participant count
- `apps/audit/apps.py` — register `CourseSignUp.kommune` field (already registered? verify; add field to tracked list if needed)

**Test:**
- `apps/courses/tests.py` (or new `tests_kommune_affiliation.py`) — model, form, migration, view tests

---

## Task 1: Create canonical kommune list module

**Files:**
- Create: `apps/schools/kommuner.py`

- [ ] **Step 1: Write the module**

```python
# apps/schools/kommuner.py
"""Canonical list of the 98 Danish kommuner.

Derived from prod data (2026-04-09) after fixing one known typo
(`Vesthimmerland Kommune` → `Vesthimmerlands Kommune`). Used as the single
source of truth for seeding the `Kommune` table and for validating kommune
dropdowns in forms.
"""

KOMMUNE_NAMES: list[str] = [
    "Aabenraa Kommune",
    "Aalborg Kommune",
    "Aarhus Kommune",
    "Albertslund Kommune",
    "Allerød Kommune",
    "Assens Kommune",
    "Ballerup Kommune",
    "Billund Kommune",
    "Bornholms Regionskommune",
    "Brøndby Kommune",
    "Brønderslev Kommune",
    "Dragør Kommune",
    "Egedal Kommune",
    "Esbjerg Kommune",
    "Faaborg-Midtfyn Kommune",
    "Fanø Kommune",
    "Favrskov Kommune",
    "Faxe Kommune",
    "Fredensborg Kommune",
    "Fredericia Kommune",
    "Frederiksberg Kommune",
    "Frederikshavn Kommune",
    "Frederikssund Kommune",
    "Furesø Kommune",
    "Gentofte Kommune",
    "Gladsaxe Kommune",
    "Glostrup Kommune",
    "Greve Kommune",
    "Gribskov Kommune",
    "Guldborgsund Kommune",
    "Haderslev Kommune",
    "Halsnæs Kommune",
    "Hedensted Kommune",
    "Helsingør Kommune",
    "Herlev Kommune",
    "Herning Kommune",
    "Hillerød Kommune",
    "Hjørring Kommune",
    "Holbæk Kommune",
    "Holstebro Kommune",
    "Horsens Kommune",
    "Hvidovre Kommune",
    "Høje-Taastrup Kommune",
    "Hørsholm Kommune",
    "Ikast-Brande Kommune",
    "Ishøj Kommune",
    "Jammerbugt Kommune",
    "Kalundborg Kommune",
    "Kerteminde Kommune",
    "Kolding Kommune",
    "Københavns Kommune",
    "Køge Kommune",
    "Langeland Kommune",
    "Lejre Kommune",
    "Lemvig Kommune",
    "Lolland Kommune",
    "Lyngby-Taarbæk Kommune",
    "Læsø Kommune",
    "Mariagerfjord Kommune",
    "Middelfart Kommune",
    "Morsø Kommune",
    "Norddjurs Kommune",
    "Nordfyns Kommune",
    "Nyborg Kommune",
    "Næstved Kommune",
    "Odder Kommune",
    "Odense Kommune",
    "Odsherred Kommune",
    "Randers Kommune",
    "Rebild Kommune",
    "Ringkøbing-Skjern Kommune",
    "Ringsted Kommune",
    "Roskilde Kommune",
    "Rudersdal Kommune",
    "Rødovre Kommune",
    "Samsø Kommune",
    "Silkeborg Kommune",
    "Skanderborg Kommune",
    "Skive Kommune",
    "Slagelse Kommune",
    "Solrød Kommune",
    "Sorø Kommune",
    "Stevns Kommune",
    "Struer Kommune",
    "Svendborg Kommune",
    "Syddjurs Kommune",
    "Sønderborg Kommune",
    "Thisted Kommune",
    "Tårnby Kommune",
    "Tønder Kommune",
    "Vallensbæk Kommune",
    "Varde Kommune",
    "Vejen Kommune",
    "Vejle Kommune",
    "Vesthimmerlands Kommune",
    "Viborg Kommune",
    "Vordingborg Kommune",
    "Ærø Kommune",
]

assert len(KOMMUNE_NAMES) == 98, f"Expected 98 kommuner, got {len(KOMMUNE_NAMES)}"
assert len(set(KOMMUNE_NAMES)) == 98, "Duplicate kommune name in KOMMUNE_NAMES"
```

- [ ] **Step 2: Verify the assertions pass**

Run: `.venv/bin/python -c "from apps.schools.kommuner import KOMMUNE_NAMES; print(len(KOMMUNE_NAMES))"`
Expected: `98`

- [ ] **Step 3: Commit**

```bash
git add apps/schools/kommuner.py
git commit -m "feat(schools): add canonical list of 98 Danish kommuner"
```

---

## Task 2: Data migration — fix Vesthimmerland typo

**Files:**
- Create: `apps/schools/migrations/0038_fix_vesthimmerland_typo.py`

- [ ] **Step 1: Write the migration**

```python
# apps/schools/migrations/0038_fix_vesthimmerland_typo.py
from django.db import migrations


def fix_typo(apps, schema_editor):
    School = apps.get_model("schools", "School")
    School.objects.filter(kommune="Vesthimmerland Kommune").update(
        kommune="Vesthimmerlands Kommune"
    )


def reverse_noop(apps, schema_editor):
    # Not reversed: we do not want to reintroduce the typo.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("schools", "0037_backfill_kommune_billing"),
    ]

    operations = [
        migrations.RunPython(fix_typo, reverse_noop),
    ]
```

- [ ] **Step 2: Apply and verify**

Run: `.venv/bin/python manage.py migrate schools 0038`
Expected: migration applies cleanly.

- [ ] **Step 3: Commit**

```bash
git add apps/schools/migrations/0038_fix_vesthimmerland_typo.py
git commit -m "fix(schools): normalize 'Vesthimmerland Kommune' typo to 'Vesthimmerlands'"
```

---

## Task 3: Data migration — seed all 98 kommuner

**Files:**
- Create: `apps/schools/migrations/0039_seed_all_kommuner.py`

- [ ] **Step 1: Write the failing test first**

Add to `apps/schools/tests_kommune.py`:

```python
from django.test import TestCase
from apps.schools.models import Kommune
from apps.schools.kommuner import KOMMUNE_NAMES


class SeedKommunerTest(TestCase):
    def test_all_98_kommuner_present(self):
        names_in_db = set(Kommune.objects.values_list("name", flat=True))
        for name in KOMMUNE_NAMES:
            self.assertIn(name, names_in_db, f"{name} missing from Kommune table")
        self.assertGreaterEqual(Kommune.objects.count(), 98)
```

- [ ] **Step 2: Run test, verify failure**

Run: `.venv/bin/python -m pytest apps/schools/tests_kommune.py::SeedKommunerTest -v`
Expected: FAIL — kommuner not yet seeded.

- [ ] **Step 3: Write the migration**

```python
# apps/schools/migrations/0039_seed_all_kommuner.py
from django.db import migrations


def seed(apps, schema_editor):
    Kommune = apps.get_model("schools", "Kommune")
    # Hardcoded here (not imported) so the migration stays stable if the
    # module is ever renamed. Mirrors apps/schools/kommuner.py::KOMMUNE_NAMES.
    names = [
        "Aabenraa Kommune", "Aalborg Kommune", "Aarhus Kommune",
        "Albertslund Kommune", "Allerød Kommune", "Assens Kommune",
        "Ballerup Kommune", "Billund Kommune", "Bornholms Regionskommune",
        "Brøndby Kommune", "Brønderslev Kommune", "Dragør Kommune",
        "Egedal Kommune", "Esbjerg Kommune", "Faaborg-Midtfyn Kommune",
        "Fanø Kommune", "Favrskov Kommune", "Faxe Kommune",
        "Fredensborg Kommune", "Fredericia Kommune", "Frederiksberg Kommune",
        "Frederikshavn Kommune", "Frederikssund Kommune", "Furesø Kommune",
        "Gentofte Kommune", "Gladsaxe Kommune", "Glostrup Kommune",
        "Greve Kommune", "Gribskov Kommune", "Guldborgsund Kommune",
        "Haderslev Kommune", "Halsnæs Kommune", "Hedensted Kommune",
        "Helsingør Kommune", "Herlev Kommune", "Herning Kommune",
        "Hillerød Kommune", "Hjørring Kommune", "Holbæk Kommune",
        "Holstebro Kommune", "Horsens Kommune", "Hvidovre Kommune",
        "Høje-Taastrup Kommune", "Hørsholm Kommune", "Ikast-Brande Kommune",
        "Ishøj Kommune", "Jammerbugt Kommune", "Kalundborg Kommune",
        "Kerteminde Kommune", "Kolding Kommune", "Københavns Kommune",
        "Køge Kommune", "Langeland Kommune", "Lejre Kommune",
        "Lemvig Kommune", "Lolland Kommune", "Lyngby-Taarbæk Kommune",
        "Læsø Kommune", "Mariagerfjord Kommune", "Middelfart Kommune",
        "Morsø Kommune", "Norddjurs Kommune", "Nordfyns Kommune",
        "Nyborg Kommune", "Næstved Kommune", "Odder Kommune",
        "Odense Kommune", "Odsherred Kommune", "Randers Kommune",
        "Rebild Kommune", "Ringkøbing-Skjern Kommune", "Ringsted Kommune",
        "Roskilde Kommune", "Rudersdal Kommune", "Rødovre Kommune",
        "Samsø Kommune", "Silkeborg Kommune", "Skanderborg Kommune",
        "Skive Kommune", "Slagelse Kommune", "Solrød Kommune",
        "Sorø Kommune", "Stevns Kommune", "Struer Kommune",
        "Svendborg Kommune", "Syddjurs Kommune", "Sønderborg Kommune",
        "Thisted Kommune", "Tårnby Kommune", "Tønder Kommune",
        "Vallensbæk Kommune", "Varde Kommune", "Vejen Kommune",
        "Vejle Kommune", "Vesthimmerlands Kommune", "Viborg Kommune",
        "Vordingborg Kommune", "Ærø Kommune",
    ]
    for name in names:
        Kommune.objects.get_or_create(name=name)


def unseed(apps, schema_editor):
    # Do not delete — may have billing info attached.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("schools", "0038_fix_vesthimmerland_typo"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
```

- [ ] **Step 4: Run test, verify pass**

Run: `.venv/bin/python -m pytest apps/schools/tests_kommune.py::SeedKommunerTest -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/schools/migrations/0039_seed_all_kommuner.py apps/schools/tests_kommune.py
git commit -m "feat(schools): seed Kommune table with all 98 Danish kommuner"
```

---

## Task 4: Add `kommune` FK to `CourseSignUp` (schema only)

**Files:**
- Modify: `apps/courses/models.py`
- Create: `apps/courses/migrations/0019_coursesignup_kommune.py`

- [ ] **Step 1: Add the field to the model**

Edit `apps/courses/models.py`. Find the `CourseSignUp` class (starts at line 136). Just after the `other_organization` field block (line 151), add:

```python
    kommune = models.ForeignKey(
        "schools.Kommune",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="course_signups",
        verbose_name="Kommune",
        help_text="Udfyldes hvis deltageren er ansat i en kommune (ikke på en skole)",
    )
```

- [ ] **Step 2: Generate the migration**

Run: `.venv/bin/python manage.py makemigrations courses --name coursesignup_kommune`
Expected: creates `apps/courses/migrations/0019_coursesignup_kommune.py` adding the FK.

- [ ] **Step 3: Apply the migration**

Run: `.venv/bin/python manage.py migrate courses`
Expected: applies cleanly.

- [ ] **Step 4: Commit**

```bash
git add apps/courses/models.py apps/courses/migrations/0019_coursesignup_kommune.py
git commit -m "feat(courses): add kommune FK to CourseSignUp"
```

---

## Task 5: Update `CourseSignUp` helpers (`organization_name`, `__str__`, `clean`)

**Files:**
- Modify: `apps/courses/models.py`
- Test: `apps/courses/tests.py` (or new file)

- [ ] **Step 1: Write the failing tests**

Add to `apps/courses/tests.py`:

```python
from django.core.exceptions import ValidationError
from apps.schools.models import Kommune


class CourseSignUpAffiliationTests(TestCase):
    def setUp(self):
        # Assume existing test fixtures provide a course; adapt if needed.
        from apps.courses.models import Course, Location
        self.location = Location.objects.create(name="Test Loc")
        self.course = Course.objects.create(
            start_date="2026-09-10", end_date="2026-09-11", location=self.location
        )
        self.kommune = Kommune.objects.create(name="Vejen Kommune")

    def _make(self, **kwargs):
        from apps.courses.models import CourseSignUp
        return CourseSignUp(
            course=self.course,
            participant_name="Mette",
            **kwargs,
        )

    def test_clean_rejects_none_set(self):
        with self.assertRaises(ValidationError):
            self._make().clean()

    def test_clean_rejects_school_and_kommune(self):
        from apps.schools.models import School
        school = School.objects.create(name="X", kommune="Vejen Kommune")
        with self.assertRaises(ValidationError):
            self._make(school=school, kommune=self.kommune).clean()

    def test_clean_rejects_kommune_and_other_org(self):
        with self.assertRaises(ValidationError):
            self._make(kommune=self.kommune, other_organization="Foo").clean()

    def test_clean_accepts_kommune_only(self):
        self._make(kommune=self.kommune).clean()  # should not raise

    def test_organization_name_uses_kommune(self):
        signup = self._make(kommune=self.kommune)
        self.assertEqual(signup.organization_name, "Vejen Kommune")

    def test_str_uses_kommune(self):
        signup = self._make(kommune=self.kommune)
        self.assertIn("Vejen Kommune", str(signup))
```

- [ ] **Step 2: Run tests, verify failures**

Run: `.venv/bin/python -m pytest apps/courses/tests.py::CourseSignUpAffiliationTests -v`
Expected: FAIL — `clean()` doesn't validate, helpers don't consult `kommune`.

- [ ] **Step 3: Update the model helpers**

In `apps/courses/models.py`, `CourseSignUp`:

Replace `__str__` (currently at ~line 176):

```python
    def __str__(self):
        return f"{self.participant_name} ({self.organization_name or 'Ukendt'})"
```

Replace `organization_name` property (~line 180):

```python
    @property
    def organization_name(self):
        """Returns the school name, kommune name, or other organization name."""
        if self.school:
            return self.school.name
        if self.kommune_id:
            return self.kommune.name
        return self.other_organization or ""
```

Add a `clean` method on `CourseSignUp` (place before `save`):

```python
    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError
        affiliations = [
            bool(self.school_id),
            bool(self.kommune_id),
            bool(self.other_organization),
        ]
        count = sum(affiliations)
        if count == 0:
            raise ValidationError(
                "Vælg skole, kommune, eller angiv en anden organisation."
            )
        if count > 1:
            raise ValidationError(
                "Angiv kun én tilknytning: skole, kommune, eller anden organisation."
            )
```

- [ ] **Step 4: Run tests, verify pass**

Run: `.venv/bin/python -m pytest apps/courses/tests.py::CourseSignUpAffiliationTests -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/courses/models.py apps/courses/tests.py
git commit -m "feat(courses): enforce XOR affiliation on CourseSignUp (school/kommune/other)"
```

---

## Task 6: Backfill data migration — move matching `other_organization` into `kommune` FK

**Files:**
- Create: `apps/courses/migrations/0020_backfill_coursesignup_kommune.py`

- [ ] **Step 1: Write the failing test**

Add to `apps/courses/tests.py`:

```python
class BackfillCourseSignUpKommuneTest(TestCase):
    """Tests that the backfill logic correctly rewrites matching other_organization."""

    def test_matching_free_text_is_moved_to_kommune_fk(self):
        from apps.courses.migrations import_module = __import__(
            "apps.courses.migrations.0020_backfill_coursesignup_kommune", fromlist=["backfill"]
        )
        # See backfill step below — we test the pure function it calls.
        # (Test body will be filled in after the migration is written.)
```

> NOTE: the migration will expose its core logic as a plain function so we can unit-test it without running the whole migration. The test body is specified in Step 3 after the function is defined.

- [ ] **Step 2: Write the migration**

```python
# apps/courses/migrations/0020_backfill_coursesignup_kommune.py
from django.db import migrations


def backfill(apps, schema_editor):
    CourseSignUp = apps.get_model("courses", "CourseSignUp")
    Kommune = apps.get_model("schools", "Kommune")

    # Build a lookup keyed on lowercase/stripped name for lenient matching.
    kommune_by_key = {
        k.name.strip().lower(): k for k in Kommune.objects.all()
    }

    updated = 0
    ambiguous = 0
    for signup in CourseSignUp.objects.filter(
        school__isnull=True,
        kommune__isnull=True,
    ).exclude(other_organization=""):
        key = (signup.other_organization or "").strip().lower()
        # Also try the key with " Kommune" appended if missing.
        match = kommune_by_key.get(key) or kommune_by_key.get(f"{key} kommune")
        if match:
            signup.kommune = match
            signup.other_organization = ""
            signup.save(update_fields=["kommune", "other_organization"])
            updated += 1
        else:
            ambiguous += 1
    print(f"[backfill] moved {updated} signups → kommune FK; {ambiguous} left as other_organization")


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0019_coursesignup_kommune"),
        ("schools", "0039_seed_all_kommuner"),
    ]

    operations = [
        migrations.RunPython(backfill, reverse_noop),
    ]
```

- [ ] **Step 3: Write the backfill unit test**

Replace the placeholder test body from Step 1 with a real end-to-end migration test using pytest-django's `migrator` is overkill; instead test via direct DB state + manual `call_command`. Add to `apps/courses/tests.py`:

```python
class BackfillCourseSignUpKommuneTest(TestCase):
    def test_backfill_matches_free_text_to_kommune(self):
        from apps.schools.models import Kommune
        from apps.courses.models import Course, CourseSignUp, Location
        # Seed kommuner (migration normally does this).
        vejen = Kommune.objects.get_or_create(name="Vejen Kommune")[0]
        Kommune.objects.get_or_create(name="Vesthimmerlands Kommune")

        loc = Location.objects.create(name="L")
        course = Course.objects.create(
            start_date="2026-09-10", end_date="2026-09-11", location=loc
        )

        matching = CourseSignUp.objects.create(
            course=course, participant_name="Mette",
            other_organization="Vejen Kommune",
        )
        ambiguous = CourseSignUp.objects.create(
            course=course, participant_name="Anna",
            other_organization="En helt anden organisation",
        )

        # Run the backfill function directly.
        from django.apps import apps as django_apps
        from apps.courses.migrations import (
            __import__ as _imp,
        )
        import importlib
        mod = importlib.import_module(
            "apps.courses.migrations.0020_backfill_coursesignup_kommune"
        )
        mod.backfill(django_apps, None)

        matching.refresh_from_db()
        ambiguous.refresh_from_db()

        self.assertEqual(matching.kommune, vejen)
        self.assertEqual(matching.other_organization, "")
        self.assertIsNone(ambiguous.kommune)
        self.assertEqual(ambiguous.other_organization, "En helt anden organisation")
```

> The module name `0020_backfill_coursesignup_kommune` starts with a digit, so `importlib.import_module` is used instead of a normal `import`.

- [ ] **Step 4: Run test, verify pass**

Run: `.venv/bin/python -m pytest apps/courses/tests.py::BackfillCourseSignUpKommuneTest -v`
Expected: PASS.

- [ ] **Step 5: Apply the migration**

Run: `.venv/bin/python manage.py migrate courses`
Expected: prints `[backfill] moved N signups → kommune FK; M left as other_organization`.

- [ ] **Step 6: Commit**

```bash
git add apps/courses/migrations/0020_backfill_coursesignup_kommune.py apps/courses/tests.py
git commit -m "feat(courses): backfill existing free-text kommune affiliations to FK"
```

---

## Task 7: Add DB-level XOR CheckConstraint

**Files:**
- Modify: `apps/courses/models.py`
- Create: `apps/courses/migrations/0021_coursesignup_affiliation_xor.py`

- [ ] **Step 1: Add the constraint to the model**

In `apps/courses/models.py`, `CourseSignUp.Meta`, replace:

```python
    class Meta:
        ordering = ["school__name", "participant_name"]
```

with:

```python
    class Meta:
        ordering = ["school__name", "participant_name"]
        constraints = [
            models.CheckConstraint(
                name="coursesignup_exactly_one_affiliation",
                check=(
                    (
                        models.Q(school__isnull=False)
                        & models.Q(kommune__isnull=True)
                        & models.Q(other_organization="")
                    )
                    | (
                        models.Q(school__isnull=True)
                        & models.Q(kommune__isnull=False)
                        & models.Q(other_organization="")
                    )
                    | (
                        models.Q(school__isnull=True)
                        & models.Q(kommune__isnull=True)
                        & ~models.Q(other_organization="")
                    )
                ),
            ),
        ]
```

- [ ] **Step 2: Generate the migration**

Run: `.venv/bin/python manage.py makemigrations courses --name coursesignup_affiliation_xor`
Expected: creates `apps/courses/migrations/0021_coursesignup_affiliation_xor.py`.

- [ ] **Step 3: Apply the migration**

Run: `.venv/bin/python manage.py migrate courses`
Expected: applies cleanly. If it fails with a constraint-violation error, the backfill in Task 6 missed rows — investigate before proceeding.

- [ ] **Step 4: Write a test that the constraint is enforced**

Add to `apps/courses/tests.py`:

```python
class CourseSignUpConstraintTest(TestCase):
    def test_db_rejects_school_and_kommune_set(self):
        from django.db import IntegrityError, transaction
        from apps.schools.models import School, Kommune
        from apps.courses.models import Course, CourseSignUp, Location
        loc = Location.objects.create(name="L")
        course = Course.objects.create(
            start_date="2026-09-10", end_date="2026-09-11", location=loc
        )
        school = School.objects.create(name="S", kommune="Vejen Kommune")
        kommune = Kommune.objects.create(name="Herning Kommune")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CourseSignUp.objects.create(
                    course=course, participant_name="X",
                    school=school, kommune=kommune,
                )
```

- [ ] **Step 5: Run test, verify pass**

Run: `.venv/bin/python -m pytest apps/courses/tests.py::CourseSignUpConstraintTest -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/courses/models.py apps/courses/migrations/0021_coursesignup_affiliation_xor.py apps/courses/tests.py
git commit -m "feat(courses): enforce XOR affiliation via DB CheckConstraint"
```

---

## Task 8: Update `CourseSignUpForm` with radio toggle + kommune field

**Files:**
- Modify: `apps/courses/forms.py`
- Test: `apps/courses/tests.py`

- [ ] **Step 1: Write failing form tests**

Add to `apps/courses/tests.py`:

```python
class CourseSignUpFormTests(TestCase):
    def setUp(self):
        from apps.courses.models import Course, Location
        from apps.schools.models import School, Kommune
        loc = Location.objects.create(name="L")
        self.course = Course.objects.create(
            start_date="2026-09-10", end_date="2026-09-11", location=loc
        )
        self.school = School.objects.create(name="Skolen", kommune="Vejen Kommune")
        self.kommune = Kommune.objects.create(name="Vejen Kommune")

    def _base(self, **overrides):
        data = {
            "course": self.course.pk,
            "participant_name": "Mette",
            "participant_email": "m@example.com",
            "participant_phone": "",
            "participant_title": "",
            "is_underviser": "on",
            "affiliation_type": "",
            "school": "",
            "kommune": "",
            "other_organization": "",
        }
        data.update(overrides)
        return data

    def test_kommune_mode_saves_kommune_fk_and_clears_others(self):
        from apps.courses.forms import CourseSignUpForm
        form = CourseSignUpForm(
            self._base(affiliation_type="kommune", kommune=self.kommune.pk,
                       school=self.school.pk, other_organization="Noise")
        )
        self.assertTrue(form.is_valid(), form.errors)
        obj = form.save()
        self.assertEqual(obj.kommune, self.kommune)
        self.assertIsNone(obj.school)
        self.assertEqual(obj.other_organization, "")

    def test_school_mode_saves_school_and_clears_others(self):
        from apps.courses.forms import CourseSignUpForm
        form = CourseSignUpForm(
            self._base(affiliation_type="school", school=self.school.pk,
                       kommune=self.kommune.pk, other_organization="Noise")
        )
        self.assertTrue(form.is_valid(), form.errors)
        obj = form.save()
        self.assertEqual(obj.school, self.school)
        self.assertIsNone(obj.kommune)
        self.assertEqual(obj.other_organization, "")

    def test_other_mode_saves_free_text(self):
        from apps.courses.forms import CourseSignUpForm
        form = CourseSignUpForm(
            self._base(affiliation_type="other", other_organization="Forvaltning XYZ",
                       school=self.school.pk, kommune=self.kommune.pk)
        )
        self.assertTrue(form.is_valid(), form.errors)
        obj = form.save()
        self.assertIsNone(obj.school)
        self.assertIsNone(obj.kommune)
        self.assertEqual(obj.other_organization, "Forvaltning XYZ")

    def test_no_affiliation_selected_is_error(self):
        from apps.courses.forms import CourseSignUpForm
        form = CourseSignUpForm(self._base(affiliation_type=""))
        self.assertFalse(form.is_valid())
```

- [ ] **Step 2: Run tests, verify failures**

Run: `.venv/bin/python -m pytest apps/courses/tests.py::CourseSignUpFormTests -v`
Expected: FAIL — `affiliation_type` not a form field, `kommune` not a field.

- [ ] **Step 3: Update the form**

In `apps/courses/forms.py`:

1. Add `Kommune` to the schools import at the top:

```python
from apps.schools.models import Kommune, School
```

2. Replace the entire `CourseSignUpForm` class:

```python
class CourseSignUpForm(forms.ModelForm):
    AFFILIATION_CHOICES = [
        ("school", "Skole"),
        ("kommune", "Kommune"),
        ("other", "Anden organisation"),
    ]
    affiliation_type = forms.ChoiceField(
        choices=AFFILIATION_CHOICES,
        widget=forms.RadioSelect,
        label="Tilknytning",
    )

    class Meta:
        model = CourseSignUp
        fields = [
            "school",
            "kommune",
            "other_organization",
            "course",
            "participant_name",
            "participant_email",
            "participant_phone",
            "participant_title",
            "is_underviser",
        ]

    def __init__(self, *args, **kwargs):
        fixed_course = kwargs.pop("course", None)
        super().__init__(*args, **kwargs)
        self.fields["school"].queryset = School.objects.active()
        self.fields["school"].required = False
        self.fields["kommune"].queryset = Kommune.objects.order_by("name")
        self.fields["kommune"].required = False
        self.fields["other_organization"].required = False
        self.fields["other_organization"].widget.attrs["placeholder"] = (
            "Fx en forvaltning, et ministerium, en virksomhed"
        )

        # Pre-select affiliation_type when editing existing instance.
        if self.instance and self.instance.pk:
            if self.instance.school_id:
                self.initial["affiliation_type"] = "school"
            elif self.instance.kommune_id:
                self.initial["affiliation_type"] = "kommune"
            elif self.instance.other_organization:
                self.initial["affiliation_type"] = "other"

        if fixed_course:
            self.fields["course"].initial = fixed_course.pk
            self.fields["course"].widget = forms.HiddenInput()

        self.helper = FormHelper()
        self.helper.layout = Layout(
            "course",
            "affiliation_type",
            Div("school", css_id="affiliation-school-field"),
            Div("kommune", css_id="affiliation-kommune-field"),
            Div("other_organization", css_id="affiliation-other-field"),
            "participant_name",
            Row(
                Column("participant_email", css_class="col-md-6"),
                Column("participant_phone", css_class="col-md-6"),
            ),
            "participant_title",
            "is_underviser",
            Submit("submit", "Gem tilmelding", css_class="btn btn-primary"),
        )

    def clean(self):
        cleaned_data = super().clean()
        affiliation = cleaned_data.get("affiliation_type")

        # Clear the fields that don't match the selected mode.
        if affiliation == "school":
            cleaned_data["kommune"] = None
            cleaned_data["other_organization"] = ""
            if not cleaned_data.get("school"):
                self.add_error("school", "Vælg en skole.")
        elif affiliation == "kommune":
            cleaned_data["school"] = None
            cleaned_data["other_organization"] = ""
            if not cleaned_data.get("kommune"):
                self.add_error("kommune", "Vælg en kommune.")
        elif affiliation == "other":
            cleaned_data["school"] = None
            cleaned_data["kommune"] = None
            if not cleaned_data.get("other_organization"):
                self.add_error("other_organization", "Angiv organisationens navn.")
        else:
            raise forms.ValidationError("Vælg tilknytning: skole, kommune eller anden organisation.")

        return cleaned_data
```

- [ ] **Step 4: Run tests, verify pass**

Run: `.venv/bin/python -m pytest apps/courses/tests.py::CourseSignUpFormTests -v`
Expected: PASS.

- [ ] **Step 5: Add JS for showing only the active field**

Locate the signup form template: `apps/courses/templates/courses/signup_form.html`. At the bottom (inside `{% block extra_js %}` or a similar block — check existing file structure), add:

```html
<script>
(function () {
  const fields = {
    school: document.getElementById("affiliation-school-field"),
    kommune: document.getElementById("affiliation-kommune-field"),
    other: document.getElementById("affiliation-other-field"),
  };
  const radios = document.querySelectorAll("input[name='affiliation_type']");

  function update() {
    const selected = document.querySelector("input[name='affiliation_type']:checked")?.value;
    for (const [key, el] of Object.entries(fields)) {
      if (!el) continue;
      el.classList.toggle("d-none", key !== selected);
    }
  }

  radios.forEach((r) => r.addEventListener("change", update));
  update();
})();
</script>
```

> If the template currently has no `{% block extra_js %}`, add the `<script>` at the very end of the file (outside any other block).

- [ ] **Step 6: Commit**

```bash
git add apps/courses/forms.py apps/courses/templates/courses/signup_form.html apps/courses/tests.py
git commit -m "feat(courses): radio toggle for school/kommune/other on signup form"
```

---

## Task 9: Extract participant list into reusable partial

**Files:**
- Create: `apps/schools/templates/schools/_participant_list.html`
- Modify: `apps/schools/templates/schools/school_detail.html`

- [ ] **Step 1: Read the current inline block**

Read `apps/schools/templates/schools/school_detail.html` lines 270–310 to capture the exact current participant-list markup.

- [ ] **Step 2: Create the partial**

Create `apps/schools/templates/schools/_participant_list.html` with the exact markup currently inside the `{% for signup in kursusdeltagere %}...{% endfor %}` loop (include the loop itself, plus the surrounding list container). The partial expects a `kursusdeltagere` context variable; callers must pass it.

Include at the top of the partial:

```django
{% load bounce_icon %}
```

(only if the original file loaded it for this block — check the existing `{% load %}` lines).

- [ ] **Step 3: Replace the inline block in `school_detail.html`**

Replace the participant-list markup (currently around lines 273–310, confirm exact range by reading the file) with:

```django
{% include "schools/_participant_list.html" %}
```

- [ ] **Step 4: Manual smoke test**

Run: `.venv/bin/python manage.py check`
Expected: no errors.

Run an existing school-detail test if one exists (grep for it):
`.venv/bin/python -m pytest apps/schools/tests.py -k school_detail -v`
Expected: PASS (or skip if none exist — acceptable).

- [ ] **Step 5: Commit**

```bash
git add apps/schools/templates/schools/_participant_list.html apps/schools/templates/schools/school_detail.html
git commit -m "refactor(schools): extract participant list to reusable partial"
```

---

## Task 10: Show participants on Kommune detail page

**Files:**
- Modify: `apps/schools/views.py` (`KommuneDetailView.get_context_data`)
- Modify: `apps/schools/templates/schools/kommune_detail.html`
- Test: `apps/schools/tests_kommune.py`

- [ ] **Step 1: Write the failing view test**

Add to `apps/schools/tests_kommune.py`:

```python
class KommuneDetailParticipantsTest(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from apps.schools.models import Kommune
        from apps.courses.models import Course, CourseSignUp, Location

        User = get_user_model()
        self.user = User.objects.create_user(
            username="staff", password="pw", is_staff=True
        )
        self.kommune = Kommune.objects.create(name="Vejen Kommune")
        loc = Location.objects.create(name="L")
        self.course = Course.objects.create(
            start_date="2025-09-10", end_date="2025-09-11", location=loc
        )
        CourseSignUp.objects.create(
            course=self.course,
            participant_name="Mette",
            kommune=self.kommune,
        )

    def test_kommune_detail_lists_kommune_participants(self):
        self.client.login(username="staff", password="pw")
        resp = self.client.get(f"/kommuner/{self.kommune.name}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Deltagere fra kommunen")
        self.assertContains(resp, "Mette")
        self.assertEqual(resp.context["stats"]["kommune_participants_count"], 1)
```

- [ ] **Step 2: Run test, verify failure**

Run: `.venv/bin/python -m pytest apps/schools/tests_kommune.py::KommuneDetailParticipantsTest -v`
Expected: FAIL — "Deltagere fra kommunen" not in response, context key missing.

- [ ] **Step 3: Update the view**

In `apps/schools/views.py`, `KommuneDetailView.get_context_data`. After the existing `context["stats"] = {...}` block (around line 109), add:

```python
        from apps.courses.models import CourseSignUp

        kursusdeltagere = (
            CourseSignUp.objects.filter(kommune__name=kommune_name)
            .select_related("course", "course__location")
            .order_by("-course__start_date", "participant_name")
        )
        context["kursusdeltagere"] = kursusdeltagere
        context["stats"]["kommune_participants_count"] = kursusdeltagere.count()
```

- [ ] **Step 4: Update the template**

Read `apps/schools/templates/schools/kommune_detail.html` first to locate the stats card and a sensible place for the new section.

In the stats card, add a new line after the existing "Tilmeldte med Kommunen betaler" line:

```django
<div class="d-flex justify-content-between">
  <span>Deltagere på kurser</span>
  <strong>{{ stats.kommune_participants_count }}</strong>
</div>
```

Below the two-column billing/stats row, add a new full-width section:

```django
<div class="card mt-4">
  <div class="card-header">
    <i class="bi bi-person-check me-2"></i>Deltagere fra kommunen
  </div>
  <div class="card-body">
    {% if kursusdeltagere %}
      {% include "schools/_participant_list.html" %}
    {% else %}
      <p class="text-muted mb-0">Ingen deltagere fra denne kommune endnu.</p>
    {% endif %}
  </div>
</div>
```

- [ ] **Step 5: Run test, verify pass**

Run: `.venv/bin/python -m pytest apps/schools/tests_kommune.py::KommuneDetailParticipantsTest -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/schools/views.py apps/schools/templates/schools/kommune_detail.html apps/schools/tests_kommune.py
git commit -m "feat(schools): show course participants on kommune detail page"
```

---

## Task 11: Register kommune field in audit config

**Files:**
- Modify: `apps/audit/apps.py`

- [ ] **Step 1: Inspect current audit config for `CourseSignUp`**

Run: `.venv/bin/python -c "import apps.audit.apps; print(open('apps/audit/apps.py').read())"`
Confirm whether `CourseSignUp` is registered and whether `kommune` is in its tracked fields (or excluded/neither — default is "all fields tracked").

- [ ] **Step 2: Ensure `kommune` is tracked**

If `CourseSignUp` uses `tracked_fields`, add `"kommune"` to the list. If it uses `excluded_fields` only (tracks everything), the new FK is tracked automatically — no change needed.

If a change is needed, edit `apps/audit/apps.py` accordingly.

- [ ] **Step 3: Run audit tests**

Run: `.venv/bin/python -m pytest apps/audit/ -v`
Expected: PASS (or no tests — acceptable).

- [ ] **Step 4: Commit (only if anything changed)**

```bash
git add apps/audit/apps.py
git commit -m "chore(audit): track kommune field on CourseSignUp"
```

---

## Task 12: CHANGELOG entry and full test run

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Add changelog entry**

Read `CHANGELOG.md` to match the existing format. Add a new entry dated today (2026-04-09):

```markdown
## 2026-04-09
- Kursusdeltagere kan nu tilknyttes direkte til en kommune, hvis de er ansat i kommunen (og ikke på en skole). På kommunesiden vises nu alle deltagere fra kommunen samlet.
```

(Phrasing in plain Danish; no mention of environments, per project preferences.)

- [ ] **Step 2: Run the full test suite**

Run: `.venv/bin/python -m pytest apps/courses apps/schools apps/audit -v`
Expected: all new tests pass; pre-existing failures in `apps/goals` and `apps/core` (noted in CLAUDE.md memory) do not affect these apps.

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: changelog entry for kommune-affiliated course participants"
```

---

## Self-Review Notes

- **Spec coverage:** data model (T4, T5, T7), canonical seed (T1, T3), typo fix (T2), backfill (T6), form UX (T8), kommune detail UI (T9, T10), audit (T11), changelog (T12), tests embedded in each task.
- **Deferred items stay deferred:** no work on `School.kommune` → FK, no changes to public signup token flow, no polymorphic abstraction.
- **One known caveat:** the `importlib.import_module` in Task 6's test targets a module whose name starts with a digit (`0020_backfill_...`); this works because `importlib` accepts dotted paths as strings. If pytest collection chokes, move the backfill logic to `apps/courses/backfill.py` and have the migration import from there — simpler and more testable.
