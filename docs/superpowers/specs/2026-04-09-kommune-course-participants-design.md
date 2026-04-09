# Kommune-affiliated course participants

**Linear:** OSO-164 (follow-up from comment 2026-03-13)
**Date:** 2026-04-09

## Background

OSO-164 shipped kommune-level billing sharing. A comment on the same issue asked for a separate capability: course participants who are employed by a kommune (not a school) should be couplable to the kommune, the same way a participant is coupled to a school. Example: Mette fra Vejen Kommune, who attended a course 10-11 Sept 2025.

Today, `CourseSignUp` has either a `school` FK or a free-text `other_organization` field. Kommune-affiliated participants end up as free text ("Vejen Kommune"), which means they aren't queryable, don't show up on any kommune page, and can't be aggregated.

## Goals

- Participants can be affiliated with a kommune as a first-class relation.
- The kommune detail page shows all participants affiliated with that kommune, mirroring how the school detail page shows participants.
- Existing free-text kommune affiliations are migrated to the new FK where possible.

## Non-goals

- Changing `School.kommune` from CharField to FK (out of scope; can follow later).
- Adding kommune affiliation to the public token-based signup form — that flow is school-scoped by design.
- A polymorphic "affiliation" abstraction covering forvaltning, region, etc.

## Data model

Add a nullable FK on `apps/courses/models.py::CourseSignUp`:

```python
kommune = models.ForeignKey(
    "schools.Kommune",
    on_delete=models.PROTECT,
    null=True, blank=True,
    related_name="course_signups",
    verbose_name="Kommune",
)
```

**XOR constraint:** exactly one of `school`, `kommune`, `other_organization` must be set. Enforced in two places:

1. `CourseSignUp.clean()` raises `ValidationError` if 0 or >1 are set.
2. A `CheckConstraint` at the DB level as a backstop:
   ```python
   CheckConstraint(
       name="coursesignup_exactly_one_affiliation",
       check=(
           (Q(school__isnull=False) & Q(kommune__isnull=True) & Q(other_organization=""))
         | (Q(school__isnull=True)  & Q(kommune__isnull=False) & Q(other_organization=""))
         | (Q(school__isnull=True)  & Q(kommune__isnull=True)  & ~Q(other_organization=""))
       ),
   )
   ```

`CourseSignUp.organization_name` and `__str__` fall back school.name → kommune.name → other_organization. Any ordering on `school__name` is updated to a computed/fallback ordering (or kept and just accepts that school-less rows sort together — decide during implementation).

**Audit:** register the new `kommune` field with the existing `CourseSignUp` audit config.

## Kommune table: canonical seed

`apps/schools/models.py::Kommune` currently only has rows for kommuner with "kommunen betaler" enabled (lazy `get_or_create_for`). For the new feature we need all 98 Danish kommuner present so the signup form can offer a dropdown.

**Prod verification (2026-04-09):** queried prod, prod's `schools_school.kommune` column already contains all 98 real Danish kommuner as distinct values, plus one typo:

- `Vesthimmerland Kommune` (missing "s") → should be `Vesthimmerlands Kommune`

Zero missing, zero extras. The seed list can therefore be built directly from the set of distinct `School.kommune` values observed in prod, minus the typo.

## Migrations

Three migrations, in order:

1. **`apps/schools/migrations/XXXX_fix_vesthimmerland_typo.py`** (data migration)
   - `UPDATE schools_school SET kommune = 'Vesthimmerlands Kommune' WHERE kommune = 'Vesthimmerland Kommune'`
   - Idempotent; no-op if already clean.

2. **`apps/schools/migrations/XXXX_seed_all_kommuner.py`** (data migration)
   - `get_or_create` a `Kommune` row for each of the 98 canonical names.
   - Canonical list committed as a Python constant in `apps/schools/kommuner.py` (used by both the migration and form validation).
   - Idempotent; existing rows (Bornholms Regionskommune, Fredensborg Kommune) are left untouched.

3. **`apps/courses/migrations/XXXX_coursesignup_kommune.py`** (schema + data)
   - Add `kommune` FK.
   - Data step: for each `CourseSignUp` with `school IS NULL` and `other_organization` matching a canonical kommune name (exact, post-typo-fix), set `kommune` FK and clear `other_organization`. Log ambiguous/unknown values without failing.
   - Add `CheckConstraint` **after** the backfill so in-flight rows don't violate it.

## Form UX

`CourseSignUpForm` gets a radio toggle **"Tilknytning"**: `Skole` / `Kommune` / `Anden organisation`. Only the field matching the selected mode is enabled; the other two are cleared on submit.

- `Skole` → existing school autocomplete.
- `Kommune` → a `ModelChoiceField` over `Kommune.objects.all()` (the seeded 98). No free-typing.
- `Anden organisation` → existing free-text CharField.

`Form.clean()` enforces XOR and scrubs inactive fields. Same widget used in create and edit.

Any admin-facing list/table that currently shows a "Skole" column changes to a "Tilknytning" column showing: school name, kommune name with a small "Kommune" badge, or free text.

## Kommune detail page

Add a **"Deltagere fra kommunen"** section below the existing stats/billing cards. Lists `CourseSignUp`s where `kommune = this`, grouped by course (course display name as heading), sorted by course date descending. Each row: participant name, title, email (with bounce warning icon if applicable), attendance status. Empty state: _"Ingen deltagere fra denne kommune endnu."_

The stats card gains a new line: **"Deltagere på kurser: N"**.

**Refactor**: the existing inline participant list in `apps/schools/templates/schools/school_detail.html` (≈ lines 273–290) is extracted to a reusable partial `schools/_participant_list.html` that takes a `kursusdeltagere` iterable. Both `school_detail.html` and the new kommune detail section include it.

## Tests

- **Model**
  - `clean()` rejects 0 or >1 affiliation fields set.
  - `CheckConstraint` rejects same at DB level.
  - `organization_name` falls back school → kommune → other_organization.
- **Form**
  - Radio toggle clears inactive fields on submit.
  - Each of the three modes round-trips via create + edit.
- **Kommune detail view**
  - Renders participants grouped by course, sorted by date desc.
  - Shows empty state when there are none.
  - Stats card reflects correct participant count.
- **Data migration**
  - Fixture includes: school-only signup, free-text matching a canonical kommune, free text with the typo `Vesthimmerland Kommune`, free text with unrecognised org.
  - After migration: kommune FK set where expected, typo normalised, unknown free text preserved as `other_organization`.
- **School detail regression**
  - Extracted `_participant_list.html` still renders correctly.

## Out of scope / deferred

- Making `School.kommune` an FK.
- Kommune affiliation in the public signup token flow.
- Polymorphic affiliation abstraction.
