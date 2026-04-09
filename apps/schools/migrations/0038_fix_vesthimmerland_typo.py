from django.db import migrations


def fix_typo(apps, schema_editor):
    School = apps.get_model("schools", "School")
    School.objects.filter(kommune="Vesthimmerland Kommune").update(kommune="Vesthimmerlands Kommune")


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
