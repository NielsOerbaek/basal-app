"""
Backfill Kommune billing rows from existing schools.

For every kommune that has at least one school with kommunen_betaler=True,
collapse the per-school fakturering_* fields into a single Kommune row,
then clear those fields on the schools (so they read from the kommune).

When schools in the same kommune have slightly diverging values (e.g. a typo
in adresse), pick the most-common non-empty value per field. If there's a
tie, the longest value wins (heuristic: longer is usually less truncated).
"""

from collections import Counter

from django.db import migrations


def _pick_canonical(values):
    cleaned = [v.strip() for v in values if v and v.strip()]
    if not cleaned:
        return ""
    counter = Counter(cleaned)
    most_common_count = counter.most_common(1)[0][1]
    candidates = [v for v, n in counter.items() if n == most_common_count]
    candidates.sort(key=lambda v: (-len(v), v))
    return candidates[0]


def backfill(apps, schema_editor):
    School = apps.get_model("schools", "School")
    Kommune = apps.get_model("schools", "Kommune")

    by_kommune = {}
    for s in School.objects.filter(kommunen_betaler=True):
        by_kommune.setdefault(s.kommune, []).append(s)

    for kommune_name, schools in by_kommune.items():
        if not kommune_name:
            continue

        canonical = {
            "fakturering_adresse": _pick_canonical([s.fakturering_adresse for s in schools]),
            "fakturering_postnummer": _pick_canonical([s.fakturering_postnummer for s in schools]),
            "fakturering_by": _pick_canonical([s.fakturering_by for s in schools]),
            "fakturering_ean_nummer": _pick_canonical([s.fakturering_ean_nummer for s in schools]),
            "fakturering_kontakt_navn": _pick_canonical([s.fakturering_kontakt_navn for s in schools]),
            "fakturering_kontakt_email": _pick_canonical([s.fakturering_kontakt_email for s in schools]),
        }

        # Preserve any existing bounce-state if all matching schools agree
        bounced = [s.fakturering_email_bounced_at for s in schools if s.fakturering_email_bounced_at]
        bounced_at = max(bounced) if bounced else None

        kommune, _ = Kommune.objects.get_or_create(name=kommune_name)
        for field, value in canonical.items():
            setattr(kommune, field, value)
        kommune.fakturering_email_bounced_at = bounced_at
        kommune.save()

        # Clear the per-school fields — they now read from the kommune
        for s in schools:
            s.fakturering_adresse = ""
            s.fakturering_postnummer = ""
            s.fakturering_by = ""
            s.fakturering_ean_nummer = ""
            s.fakturering_kontakt_navn = ""
            s.fakturering_kontakt_email = ""
            s.fakturering_email_bounced_at = None
            s.save(
                update_fields=[
                    "fakturering_adresse",
                    "fakturering_postnummer",
                    "fakturering_by",
                    "fakturering_ean_nummer",
                    "fakturering_kontakt_navn",
                    "fakturering_kontakt_email",
                    "fakturering_email_bounced_at",
                ]
            )


def reverse_backfill(apps, schema_editor):
    """Best-effort reverse: copy kommune billing back onto every school with kommunen_betaler=True."""
    School = apps.get_model("schools", "School")
    Kommune = apps.get_model("schools", "Kommune")

    for kommune in Kommune.objects.all():
        for s in School.objects.filter(kommunen_betaler=True, kommune=kommune.name):
            s.fakturering_adresse = kommune.fakturering_adresse
            s.fakturering_postnummer = kommune.fakturering_postnummer
            s.fakturering_by = kommune.fakturering_by
            s.fakturering_ean_nummer = kommune.fakturering_ean_nummer
            s.fakturering_kontakt_navn = kommune.fakturering_kontakt_navn
            s.fakturering_kontakt_email = kommune.fakturering_kontakt_email
            s.fakturering_email_bounced_at = kommune.fakturering_email_bounced_at
            s.save()
        kommune.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("schools", "0036_kommune"),
    ]

    operations = [
        migrations.RunPython(backfill, reverse_backfill),
    ]
