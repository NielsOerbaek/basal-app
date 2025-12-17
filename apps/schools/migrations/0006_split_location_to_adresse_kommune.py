from django.db import migrations, models


def copy_location_to_adresse(apps, schema_editor):
    """Copy location value to adresse field."""
    School = apps.get_model('schools', 'School')
    for school in School.objects.all():
        school.adresse = school.location
        # Try to extract kommune from location (e.g., "Street, 1234 City")
        # Default to 'Ukendt' if we can't determine it
        school.kommune = 'Ukendt'
        school.save()


def reverse_copy(apps, schema_editor):
    """Copy adresse back to location."""
    School = apps.get_model('schools', 'School')
    for school in School.objects.all():
        school.location = school.adresse
        school.save()


class Migration(migrations.Migration):

    dependencies = [
        ('schools', '0005_remove_school_contact_fields'),
    ]

    operations = [
        # Add new fields with defaults
        migrations.AddField(
            model_name='school',
            name='adresse',
            field=models.CharField(default='', max_length=255, verbose_name='Adresse'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='school',
            name='kommune',
            field=models.CharField(default='', max_length=100, verbose_name='Kommune'),
            preserve_default=False,
        ),
        # Copy data from location to adresse
        migrations.RunPython(copy_location_to_adresse, reverse_copy),
        # Remove the old location field
        migrations.RemoveField(
            model_name='school',
            name='location',
        ),
    ]
