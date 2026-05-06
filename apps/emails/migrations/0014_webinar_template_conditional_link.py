from django.db import migrations

# Body shipped by 0013_update_webinar_template_body — the previous "current"
# template, before this migration upgrades it.
OLD_BODY = """<p>Hej {{ participant_name }},</p>

<p>Tak for din tilmelding til webinaret <strong>{{ webinar_title }}</strong>.</p>

<p><strong>Hvornår:</strong> {{ webinar_time }}</p>

{% if instructors %}<p><strong>Oplægsholdere:</strong> {{ instructors }}</p>{% endif %}

<p><strong>Mødelink:</strong> <a href="{{ meeting_url }}">{{ meeting_url }}</a></p>

{% if webinar_description %}<hr>{{ webinar_description|safe }}{% endif %}

<p>Vi glæder os til at se dig.</p>
<p>Mvh.<br>Basal</p>"""

NEW_BODY = """<p>Hej {{ participant_name }},</p>

<p>Tak for din tilmelding til webinaret <strong>{{ webinar_title }}</strong>.</p>

<p><strong>Hvornår:</strong> {{ webinar_time }}</p>

{% if instructors %}<p><strong>Oplægsholdere:</strong> {{ instructors }}</p>{% endif %}

{% if meeting_url %}<p><strong>Mødelink:</strong> <a href="{{ meeting_url }}">{{ meeting_url }}</a></p>{% else %}<p><strong>Mødelink:</strong> Mødelinket eftersendes tættere på datoen.</p>{% endif %}

{% if webinar_description %}<hr>{{ webinar_description|safe }}{% endif %}

<p>Vi glæder os til at se dig.</p>
<p>Mvh.<br>Basal</p>"""


def upgrade(apps, schema_editor):
    """Wrap the meeting-link block in a {% if meeting_url %}...{% else %}...{% endif %},
    but only if the body still matches the previous shipped version. An admin who has
    customised the template keeps their version."""
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
        ("emails", "0013_update_webinar_template_body"),
    ]

    operations = [
        migrations.RunPython(upgrade, downgrade),
    ]
