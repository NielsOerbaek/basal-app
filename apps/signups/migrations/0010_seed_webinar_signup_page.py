from django.db import migrations

SUCCESS_MESSAGE = "<p>Tak for din tilmelding. Du modtager en bekræftelse på e-mail med mødelinket.</p>"


def seed(apps, schema_editor):
    SignupPage = apps.get_model("signups", "SignupPage")
    SignupPage.objects.update_or_create(
        page_type="webinar_signup",
        defaults={
            "title": "Webinartilmelding",
            "subtitle": "",
            "intro_text": "",
            "success_title": "Tilmelding gennemført",
            "success_message": SUCCESS_MESSAGE,
            "submit_button_text": "Tilmeld",
            "is_active": True,
        },
    )


def unseed(apps, schema_editor):
    SignupPage = apps.get_model("signups", "SignupPage")
    SignupPage.objects.filter(page_type="webinar_signup").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("signups", "0009_alter_signuppage_page_type"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
