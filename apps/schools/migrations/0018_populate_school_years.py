# Generated manually for school year standardization

from datetime import date

from django.db import migrations


def populate_school_years(apps, schema_editor):
    """
    Populate SchoolYear records for past 10 and next 50 years.

    Uses canonical "YYYY/YY" format (e.g., "2024/25").
    School years run from August 1 to July 31.
    """
    SchoolYear = apps.get_model("schools", "SchoolYear")

    current_year = date.today().year
    start_year = current_year - 10
    end_year = current_year + 50

    # First, fix any existing records with wrong format (e.g., "2025-2026" -> "2025/26")
    for sy in SchoolYear.objects.all():
        if "-" in sy.name and len(sy.name) == 9:  # "2025-2026" format
            # Convert to canonical format
            first_year = sy.name[:4]
            second_year = sy.name[5:9]
            new_name = f"{first_year}/{second_year[2:]}"

            # Check if canonical name already exists
            if not SchoolYear.objects.filter(name=new_name).exists():
                sy.name = new_name
                sy.save()
            else:
                # Canonical version exists, delete the duplicate
                sy.delete()

    # Create school years for the range
    for year in range(start_year, end_year + 1):
        name = f"{year}/{str(year + 1)[2:]}"
        start_date = date(year, 8, 1)
        end_date = date(year + 1, 7, 31)

        SchoolYear.objects.get_or_create(
            name=name,
            defaults={
                "start_date": start_date,
                "end_date": end_date,
            },
        )


def reverse_populate(apps, schema_editor):
    """
    Reverse migration - removes auto-generated school years.

    Note: This keeps any school years that have related invoices.
    """
    SchoolYear = apps.get_model("schools", "SchoolYear")

    current_year = date.today().year
    start_year = current_year - 10
    end_year = current_year + 50

    for year in range(start_year, end_year + 1):
        name = f"{year}/{str(year + 1)[2:]}"
        # Only delete if no invoices are linked
        SchoolYear.objects.filter(name=name, invoices__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("schools", "0017_add_unique_school_constraint"),
    ]

    operations = [
        migrations.RunPython(populate_school_years, reverse_populate),
    ]
