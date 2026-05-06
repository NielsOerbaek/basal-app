from django.db import migrations

OLD_BODY = """<p>Hej {{ participant_name }},</p>

<p>Tak for din tilmelding til webinaret <strong>{{ webinar_title }}</strong>.</p>

<p><strong>Hvornår:</strong> {{ webinar_date }}<br>
<strong>Varighed:</strong> {{ webinar_duration }} minutter</p>

{% if instructors %}<p><strong>Undervisere:</strong> {{ instructors }}</p>{% endif %}

<p><strong>Mødelink:</strong> <a href="{{ meeting_url }}">{{ meeting_url }}</a></p>

{% if webinar_description %}<hr>{{ webinar_description|safe }}{% endif %}

<p>Vi glæder os til at se dig.</p>
<p>Mvh.<br>Basal</p>"""

NEW_BODY = """<p>Hej {{ participant_name }},</p>

<p>Tak for din tilmelding til webinaret <strong>{{ webinar_title }}</strong>.</p>

<p><strong>Hvornår:</strong> {{ webinar_time }}</p>

{% if instructors %}<p><strong>Oplægsholdere:</strong> {{ instructors }}</p>{% endif %}

<p><strong>Mødelink:</strong> <a href="{{ meeting_url }}">{{ meeting_url }}</a></p>

{% if webinar_description %}<hr>{{ webinar_description|safe }}{% endif %}

<p>Vi glæder os til at se dig.</p>
<p>Mvh.<br>Basal</p>"""


def upgrade(apps, schema_editor):
    """Replace the seeded webinar template body, but only if it still
    matches the original — leave admin-edited templates alone."""
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    try:
        template = EmailTemplate.objects.get(email_type="webinar_confirmation")
    except EmailTemplate.DoesNotExist:
        return
    if template.body_html.strip() == OLD_BODY.strip():
        template.body_html = NEW_BODY
        template.save(update_fields=["body_html"])


def downgrade(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    try:
        template = EmailTemplate.objects.get(email_type="webinar_confirmation")
    except EmailTemplate.DoesNotExist:
        return
    if template.body_html.strip() == NEW_BODY.strip():
        template.body_html = OLD_BODY
        template.save(update_fields=["body_html"])


class Migration(migrations.Migration):
    dependencies = [
        ("emails", "0012_seed_webinar_template"),
    ]

    operations = [
        migrations.RunPython(upgrade, downgrade),
    ]
