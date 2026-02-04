from django.db import migrations
from django.db.models import F


def copy_enrolled_at_to_active_from(apps, schema_editor):
    School = apps.get_model("schools", "School")
    School.objects.filter(
        enrolled_at__isnull=False,
        active_from__isnull=True,
    ).update(active_from=F("enrolled_at"))


def reverse_migration(apps, schema_editor):
    # No reverse needed - active_from can stay populated
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("schools", "0028_add_active_from_field"),
    ]

    operations = [
        migrations.RunPython(copy_enrolled_at_to_active_from, reverse_migration),
    ]
