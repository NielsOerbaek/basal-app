from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bulk_email", "0006_backfill_recipient_bounced_at"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bulkemail",
            name="recipient_type",
            field=models.CharField(
                choices=[
                    ("koordinator", "Koordinator"),
                    ("oekonomisk_ansvarlig", "Økonomiansvarlig"),
                    ("begge", "Koordinator + Økonomiansvarlig"),
                    ("foerste_kontakt", "Første kontakt"),
                    ("alle_kontakter", "Alle kontakter"),
                    ("undervisere_kursus", "Undervisere der har deltaget på kursus"),
                ],
                max_length=30,
            ),
        ),
    ]
