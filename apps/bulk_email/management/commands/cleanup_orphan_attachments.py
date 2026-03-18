from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.bulk_email.models import BulkEmailAttachment


class Command(BaseCommand):
    help = "Delete BulkEmailAttachment records not linked to any BulkEmail and older than 24 hours"

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(hours=24)
        orphans = BulkEmailAttachment.objects.filter(bulk_email__isnull=True, uploaded_at__lt=cutoff)
        count = orphans.count()
        for attachment in orphans:
            attachment.file.delete(save=False)
            attachment.delete()
        self.stdout.write(f"Deleted {count} orphan attachment(s).")
