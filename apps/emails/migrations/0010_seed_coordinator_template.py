from django.db import migrations

DESCRIPTIONS = {
    "signup_confirmation": "Sendes til hver deltager ved kursustilmelding.",
    "course_reminder": "Sendes til hver deltager 14 dage før kursusstart. Kursusmateriale vedhæftes automatisk.",
    "school_enrollment_confirmation": "Sendes til både koordinator og økonomisk ansvarlig når en skole tilmelder sig Basal.",
    "coordinator_signup": "Sendes til skolens koordinator når deltagere tilmeldes et kursus. Indeholder oversigt over tilmeldte deltagere. Modtager kan ændres til en anden e-mail ved tilmelding.",
}


def seed_data(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")

    # Update descriptions on existing templates
    for email_type, description in DESCRIPTIONS.items():
        EmailTemplate.objects.filter(email_type=email_type).update(description=description)

    # Create coordinator template if it doesn't exist
    EmailTemplate.objects.get_or_create(
        email_type="coordinator_signup",
        defaults={
            "subject": "Kursustilmelding – {{ school_name }}",
            "body_html": (
                "<p>Kære {{ coordinator_name }},</p>"
                "<p>Følgende deltagere fra {{ school_name }} er blevet tilmeldt kurset "
                "<strong>{{ course_title }}</strong>:</p>"
                "{{ participants_list }}"
                "<p><strong>Kursusdetaljer:</strong></p>"
                "<ul>"
                "    <li>Dato: {{ course_date }}</li>"
                "    <li>Sted: {{ course_location }}</li>"
                "</ul>"
                "<p>Med venlig hilsen,<br>Basal</p>"
            ),
            "is_active": True,
            "description": DESCRIPTIONS["coordinator_signup"],
        },
    )


def unseed_data(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    EmailTemplate.objects.filter(email_type="coordinator_signup").delete()
    EmailTemplate.objects.all().update(description="")


class Migration(migrations.Migration):
    dependencies = [
        ("emails", "0009_add_description_and_coordinator_type"),
    ]

    operations = [
        migrations.RunPython(seed_data, unseed_data),
    ]
