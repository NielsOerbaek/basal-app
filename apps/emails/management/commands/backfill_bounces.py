"""One-off command to backfill email_bounced_at from a CSV of bounced emails."""

import csv

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.emails.views import mark_email_bounced


class Command(BaseCommand):
    help = "Backfill email_bounced_at from a CSV export of bounced emails"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", help="Path to CSV file with bounced emails")

    def handle(self, *args, **options):
        with open(options["csv_file"]) as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                email = row["to"].strip()
                bounced_at = row.get("sent_at") or row.get("created_at")
                ts = parse_datetime(bounced_at) if bounced_at else timezone.now()
                mark_email_bounced(email, at=ts)
                count += 1
                self.stdout.write(f"  Marked: {email}")

        self.stdout.write(self.style.SUCCESS(f"Done — processed {count} bounced emails"))
