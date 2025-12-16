from django.contrib.auth.hashers import make_password
from django.db import migrations


def create_superuser(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    if not User.objects.filter(username='admin').exists():
        User.objects.create(
            username='admin',
            email='admin@example.com',
            first_name='Admin',
            last_name='User',
            is_staff=True,
            is_superuser=True,
            is_active=True,
            password=make_password('admin'),
        )


def remove_superuser(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    User.objects.filter(username='admin').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('auth', '__first__'),
    ]

    operations = [
        migrations.RunPython(create_superuser, remove_superuser),
    ]
