from django.db import migrations


def create_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")

    # Create permission groups
    Group.objects.get_or_create(name="Brugeradministrator")
    Group.objects.get_or_create(name="Tilmeldingsadministrator")


def remove_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=["Brugeradministrator", "Tilmeldingsadministrator"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_create_dev_superuser"),
        ("auth", "__first__"),
    ]

    operations = [
        migrations.RunPython(create_groups, remove_groups),
    ]
