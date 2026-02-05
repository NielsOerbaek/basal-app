# Data migration to update reminder email template from 2 to 14 days

from django.db import migrations


def update_template_text(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    template = EmailTemplate.objects.filter(email_type="course_reminder").first()
    if template:
        template.subject = template.subject.replace("om 2 dage", "om 14 dage")
        template.body_html = template.body_html.replace("om 2 dage", "om 14 dage").replace("2 dage før", "14 dage før")
        template.save()

    # Also update the signup confirmation template that mentions "2 dage før"
    confirmation = EmailTemplate.objects.filter(email_type="signup_confirmation").first()
    if confirmation:
        confirmation.body_html = confirmation.body_html.replace("2 dage før", "14 dage før")
        confirmation.save()


def reverse_template_text(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    template = EmailTemplate.objects.filter(email_type="course_reminder").first()
    if template:
        template.subject = template.subject.replace("om 14 dage", "om 2 dage")
        template.body_html = template.body_html.replace("om 14 dage", "om 2 dage").replace("14 dage før", "2 dage før")
        template.save()

    confirmation = EmailTemplate.objects.filter(email_type="signup_confirmation").first()
    if confirmation:
        confirmation.body_html = confirmation.body_html.replace("14 dage før", "2 dage før")
        confirmation.save()


class Migration(migrations.Migration):
    dependencies = [
        ("emails", "0007_update_reminder_label"),
    ]

    operations = [
        migrations.RunPython(update_template_text, reverse_template_text),
    ]
