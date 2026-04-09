"""Core logic for moving free-text kommune affiliations into the kommune FK.

Imported by the 0020 data migration and directly by tests.
"""


def backfill_kommune_affiliations(CourseSignUp, Kommune):
    """Rewrite CourseSignUp rows where other_organization matches a Kommune name.

    Args:
        CourseSignUp: the CourseSignUp model class (real or migration-historical)
        Kommune: the Kommune model class (real or migration-historical)

    Returns:
        (updated_count, ambiguous_count)
    """
    kommune_by_key = {k.name.strip().lower(): k for k in Kommune.objects.all()}

    updated = 0
    ambiguous = 0
    qs = CourseSignUp.objects.filter(
        school__isnull=True,
        kommune__isnull=True,
    ).exclude(other_organization="")
    for signup in qs:
        key = (signup.other_organization or "").strip().lower()
        match = kommune_by_key.get(key) or kommune_by_key.get(f"{key} kommune")
        if match:
            signup.kommune = match
            signup.other_organization = ""
            signup.save(update_fields=["kommune", "other_organization"])
            updated += 1
        else:
            ambiguous += 1
    return updated, ambiguous
