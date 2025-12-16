from django.db import migrations


def create_dev_superuser(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Employee = apps.get_model('accounts', 'Employee')

    # Only create if the user doesn't exist
    if not User.objects.filter(username='admin').exists():
        user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin',
            first_name='Admin',
            last_name='User',
        )
        Employee.objects.create(user=user)


def remove_dev_superuser(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    User.objects.filter(username='admin').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_dev_superuser, remove_dev_superuser),
    ]
