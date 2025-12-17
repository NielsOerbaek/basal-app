from django.db import migrations


def migrate_contacts_to_person(apps, schema_editor):
    School = apps.get_model('schools', 'School')
    Person = apps.get_model('schools', 'Person')

    for school in School.objects.all():
        if school.contact_name:
            Person.objects.create(
                school=school,
                name=school.contact_name,
                email=school.contact_email or '',
                phone=school.contact_phone or '',
                role='koordinator',
                is_primary=True,
            )


def reverse_migration(apps, schema_editor):
    Person = apps.get_model('schools', 'Person')
    Person.objects.filter(is_primary=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('schools', '0003_add_person_and_schoolcomment'),
    ]

    operations = [
        migrations.RunPython(migrate_contacts_to_person, reverse_migration),
    ]
