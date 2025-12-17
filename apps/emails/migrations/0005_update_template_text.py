# Generated migration to update email template text

from django.db import migrations


def update_templates(apps, schema_editor):
    EmailTemplate = apps.get_model('emails', 'EmailTemplate')

    # Update signup confirmation template
    EmailTemplate.objects.filter(email_type='signup_confirmation').update(
        body_html='''<p>Kære {{ participant_name }},</p>

<p>Tak for din tilmelding! Du er tilmeldt kurset <strong>{{ course_title }}</strong> som deltager fra {{ school_name }}.</p>

<p><strong>Kursusdetaljer:</strong></p>
<ul>
    <li>Dato: {{ course_date }}</li>
    <li>Sted: {{ course_location }}</li>
</ul>

<p>Du vil modtage en påmindelse med kursusmateriale 2 dage før kurset.</p>

<p>Med venlig hilsen,<br>
Basal</p>'''
    )

    # Update course reminder template
    EmailTemplate.objects.filter(email_type='course_reminder').update(
        body_html='''<p>Kære {{ participant_name }},</p>

<p>Dette er en påmindelse om, at du er tilmeldt kurset <strong>{{ course_title }}</strong> som deltager fra {{ school_name }}. Kurset starter om 2 dage.</p>

<p><strong>Kursusdetaljer:</strong></p>
<ul>
    <li>Dato: {{ course_date }}</li>
    <li>Sted: {{ course_location }}</li>
</ul>

<p>Hvis der er vedhæftet kursusmateriale til denne e-mail, bedes du læse det igennem før kurset.</p>

<p>Vi glæder os til at se dig!</p>

<p>Med venlig hilsen,<br>
Basal</p>'''
    )


def revert_templates(apps, schema_editor):
    EmailTemplate = apps.get_model('emails', 'EmailTemplate')

    # Revert to original templates
    EmailTemplate.objects.filter(email_type='signup_confirmation').update(
        body_html='''<p>Kære {{ participant_name }},</p>

<p>Tak for din tilmelding til kurset <strong>{{ course_title }}</strong>.</p>

<p><strong>Kursusdetaljer:</strong></p>
<ul>
    <li>Dato: {{ course_date }}</li>
    <li>Sted: {{ course_location }}</li>
    <li>Skole: {{ school_name }}</li>
</ul>

<p>Du vil modtage en påmindelse med kursusmateriale 2 dage før kurset.</p>

<p>Med venlig hilsen,<br>
Basal</p>'''
    )

    EmailTemplate.objects.filter(email_type='course_reminder').update(
        body_html='''<p>Kære {{ participant_name }},</p>

<p>Dette er en påmindelse om, at du er tilmeldt kurset <strong>{{ course_title }}</strong>, som starter om 2 dage.</p>

<p><strong>Kursusdetaljer:</strong></p>
<ul>
    <li>Dato: {{ course_date }}</li>
    <li>Sted: {{ course_location }}</li>
    <li>Skole: {{ school_name }}</li>
</ul>

<p>Hvis der er vedhæftet kursusmateriale til denne e-mail, bedes du læse det igennem før kurset.</p>

<p>Vi glæder os til at se dig!</p>

<p>Med venlig hilsen,<br>
Basal</p>'''
    )


class Migration(migrations.Migration):
    dependencies = [
        ("emails", "0004_remove_template_attachment"),
    ]

    operations = [
        migrations.RunPython(update_templates, revert_templates),
    ]
