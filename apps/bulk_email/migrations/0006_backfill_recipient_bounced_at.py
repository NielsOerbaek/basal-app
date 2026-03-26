"""Backfill bounced_at on BulkEmailRecipient from Person.email_bounced_at."""

from django.db import migrations


def backfill_bounced_at(apps, schema_editor):
    Person = apps.get_model("schools", "Person")
    BulkEmailRecipient = apps.get_model("bulk_email", "BulkEmailRecipient")

    # Build a map of bounced emails -> bounced_at timestamp
    bounced_map = {}
    for email, bounced_at in Person.objects.filter(email_bounced_at__isnull=False).values_list(
        "email", "email_bounced_at"
    ):
        bounced_map[email.lower()] = bounced_at

    if not bounced_map:
        return

    for recipient in BulkEmailRecipient.objects.filter(success=True, bounced_at__isnull=True):
        bounced_at = bounced_map.get(recipient.email.lower())
        if bounced_at:
            recipient.bounced_at = bounced_at
            recipient.save(update_fields=["bounced_at"])


class Migration(migrations.Migration):
    dependencies = [
        ("bulk_email", "0005_bulkemailrecipient_bounced_at"),
        ("schools", "0033_person_email_bounced_at_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_bounced_at, migrations.RunPython.noop),
    ]
