from django.db import migrations


def migrate_person_roles(apps, schema_editor):
    Person = apps.get_model("schools", "Person")

    for person in Person.objects.select_related("school").all():
        school_enrolled = person.school.enrolled_at is not None and (
            person.school.opted_out_at is None or person.school.opted_out_at > person.school.enrolled_at
        )

        # Migrate is_primary for enrolled schools only
        if person.is_primary and school_enrolled:
            person.is_koordinator = True

        # Migrate existing role values (all schools)
        if person.role == "koordinator":
            person.is_koordinator = True
        elif person.role == "oekonomisk_ansvarlig":
            person.is_oekonomisk_ansvarlig = True

        person.save(update_fields=["is_koordinator", "is_oekonomisk_ansvarlig"])


def reverse_migrate(apps, schema_editor):
    Person = apps.get_model("schools", "Person")

    for person in Person.objects.all():
        if person.is_koordinator:
            person.role = "koordinator"
            person.is_primary = True
        elif person.is_oekonomisk_ansvarlig:
            person.role = "oekonomisk_ansvarlig"
        else:
            person.role = "andet"
        person.save(update_fields=["role", "is_primary"])


class Migration(migrations.Migration):
    dependencies = [
        ("schools", "0025_add_koordinator_fields"),
    ]

    operations = [
        migrations.RunPython(migrate_person_roles, reverse_migrate),
    ]
