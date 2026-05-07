from django.db import migrations, models


def backfill_recipient_types(apps, schema_editor):
    BulkEmail = apps.get_model("bulk_email", "BulkEmail")
    for campaign in BulkEmail.objects.all():
        old = campaign.recipient_type
        if old == "begge":
            campaign.recipient_types = ["koordinator", "oekonomisk_ansvarlig"]
        elif old:
            campaign.recipient_types = [old]
        else:
            campaign.recipient_types = []
        campaign.save(update_fields=["recipient_types"])


def reverse_backfill(apps, schema_editor):
    BulkEmail = apps.get_model("bulk_email", "BulkEmail")
    for campaign in BulkEmail.objects.all():
        types = campaign.recipient_types or []
        if set(types) == {"koordinator", "oekonomisk_ansvarlig"}:
            campaign.recipient_type = "begge"
        elif types:
            campaign.recipient_type = types[0]
        else:
            campaign.recipient_type = ""
        campaign.save(update_fields=["recipient_type"])


class Migration(migrations.Migration):
    dependencies = [
        ("bulk_email", "0007_add_undervisere_kursus_choice"),
    ]

    operations = [
        migrations.AddField(
            model_name="bulkemail",
            name="recipient_types",
            field=models.JSONField(default=list),
        ),
        migrations.RunPython(backfill_recipient_types, reverse_backfill),
        migrations.RemoveField(
            model_name="bulkemail",
            name="recipient_type",
        ),
    ]
