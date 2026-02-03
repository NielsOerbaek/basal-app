from django.db import migrations

# Mapping from role_other values (set by migration 0022) to titel choices
ROLE_OTHER_TO_TITEL = {
    "Skoleleder": "skoleleder",
    "Udskolingsleder": "udskolingsleder",
}


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

        # Migrate role_other to titel (if titel is not already set)
        if not person.titel and person.role_other:
            if person.role_other in ROLE_OTHER_TO_TITEL:
                # Known job title - map to titel choice
                person.titel = ROLE_OTHER_TO_TITEL[person.role_other]
            else:
                # Custom title - put in titel_other
                person.titel = "andet"
                person.titel_other = person.role_other

        person.save(update_fields=["is_koordinator", "is_oekonomisk_ansvarlig", "titel", "titel_other"])


def reverse_migrate(apps, schema_editor):
    Person = apps.get_model("schools", "Person")

    # Reverse mapping
    titel_to_role_other = {v: k for k, v in ROLE_OTHER_TO_TITEL.items()}

    for person in Person.objects.all():
        if person.is_koordinator:
            person.role = "koordinator"
            person.is_primary = True
        elif person.is_oekonomisk_ansvarlig:
            person.role = "oekonomisk_ansvarlig"
        else:
            person.role = "andet"

        # Reverse titel migration
        if person.titel in titel_to_role_other:
            person.role_other = titel_to_role_other[person.titel]
            person.titel = ""
        elif person.titel == "andet" and person.titel_other:
            person.role_other = person.titel_other
            person.titel = ""
            person.titel_other = ""

        person.save(update_fields=["role", "is_primary", "role_other", "titel", "titel_other"])


class Migration(migrations.Migration):
    dependencies = [
        ("schools", "0025_add_koordinator_fields"),
    ]

    operations = [
        migrations.RunPython(migrate_person_roles, reverse_migrate),
    ]
