from django.db import migrations

from apps.courses.kommune_backfill import backfill_kommune_affiliations


def backfill(apps, schema_editor):
    CourseSignUp = apps.get_model("courses", "CourseSignUp")
    Kommune = apps.get_model("schools", "Kommune")
    updated, ambiguous = backfill_kommune_affiliations(CourseSignUp, Kommune)
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
