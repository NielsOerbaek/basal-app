import gzip
import os
import subprocess
import tarfile
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Backup database and media files to S3-compatible storage or local storage"

    def add_arguments(self, parser):
        parser.add_argument(
            "--retention-days",
            type=int,
            default=30,
            help="Number of days to keep backups (default: 30)",
        )
        parser.add_argument(
            "--local-only",
            action="store_true",
            help="Store backup locally only (skip S3 upload)",
        )
        parser.add_argument(
            "--backup-dir",
            type=str,
            default="/app/backups",
            help="Local backup directory (default: /app/backups)",
        )
        parser.add_argument(
            "--skip-media",
            action="store_true",
            help="Skip media files backup (database only)",
        )

    def handle(self, *args, **options):
        local_only = options["local_only"]
        backup_dir = Path(options["backup_dir"])
        skip_media = options["skip_media"]

        # Check S3 settings if not local-only
        s3 = None
        if not local_only:
            s3 = self._get_s3_client()
            if not s3:
                self.stdout.write(self.style.WARNING("S3 settings missing, using local-only mode"))
                local_only = True

        # Create backup directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        local_backup_dir = backup_dir / backup_name
        local_backup_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write(f"Creating backup: {backup_name}")

        # Backup database
        db_success = self._backup_database(local_backup_dir, s3, backup_name, local_only)
        if not db_success:
            return

        # Backup media files
        if not skip_media:
            self._backup_media(local_backup_dir, s3, backup_name, local_only)

        # Clean up old backups
        self._cleanup_local_backups(backup_dir, options["retention_days"])
        if not local_only and s3:
            self._cleanup_s3_backups(s3, options["retention_days"])

        self.stdout.write(self.style.SUCCESS(f"Backup completed: {backup_name}"))

    def _get_s3_client(self):
        """Get S3 client if configured."""
        required_settings = ["S3_ACCESS_KEY", "S3_SECRET_KEY", "S3_BUCKET_NAME", "S3_ENDPOINT"]
        missing = [s for s in required_settings if not getattr(settings, s, None)]
        if missing:
            return None

        try:
            import boto3
            from botocore.config import Config

            return boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
                config=Config(
                    signature_version="s3v4",
                    retries={"max_attempts": 3, "mode": "standard"},
                ),
            )
        except Exception as e:
            self.stderr.write(self.style.WARNING(f"Failed to create S3 client: {e}"))
            return None

    def _backup_database(self, local_backup_dir, s3, backup_name, local_only):
        """Backup PostgreSQL database."""
        import dj_database_url

        db_config = dj_database_url.config()

        if not db_config:
            self.stderr.write(self.style.ERROR("DATABASE_URL not configured"))
            return False

        self.stdout.write("Backing up database...")

        env = os.environ.copy()
        env["PGPASSWORD"] = db_config.get("PASSWORD", "")

        pg_dump_cmd = [
            "pg_dump",
            "-h",
            db_config.get("HOST", "localhost"),
            "-p",
            str(db_config.get("PORT", 5432)),
            "-U",
            db_config.get("USER", "postgres"),
            "-d",
            db_config.get("NAME", "basal"),
            "--no-owner",
            "--no-acl",
        ]

        try:
            result = subprocess.run(
                pg_dump_cmd,
                env=env,
                capture_output=True,
                check=True,
            )

            compressed_data = gzip.compress(result.stdout)
            db_filename = "database.sql.gz"
            local_path = local_backup_dir / db_filename

            local_path.write_bytes(compressed_data)
            self.stdout.write(f"  Database backup: {len(compressed_data) / 1024:.1f} KB")

            if not local_only and s3:
                s3.put_object(
                    Bucket=settings.S3_BUCKET_NAME,
                    Key=f"backups/{backup_name}/{db_filename}",
                    Body=compressed_data,
                    ContentType="application/gzip",
                )
                self.stdout.write(self.style.SUCCESS(f"  Uploaded to S3: {backup_name}/{db_filename}"))

            return True

        except subprocess.CalledProcessError as e:
            self.stderr.write(self.style.ERROR(f"pg_dump failed: {e.stderr.decode()}"))
            return False
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR("pg_dump not found. Install postgresql-client."))
            return False
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Database backup failed: {e}"))
            return False

    def _backup_media(self, local_backup_dir, s3, backup_name, local_only):
        """Backup media files."""
        media_root = Path(settings.MEDIA_ROOT)

        if not media_root.exists():
            self.stdout.write("  No media directory found, skipping media backup")
            return

        # Check if there are any files to backup
        media_files = list(media_root.rglob("*"))
        media_files = [f for f in media_files if f.is_file()]

        if not media_files:
            self.stdout.write("  No media files to backup")
            return

        self.stdout.write(f"Backing up {len(media_files)} media file(s)...")

        try:
            media_filename = "media.tar.gz"
            local_path = local_backup_dir / media_filename

            # Create tar.gz archive
            with tarfile.open(local_path, "w:gz") as tar:
                tar.add(media_root, arcname="media")

            file_size = local_path.stat().st_size
            self.stdout.write(f"  Media backup: {file_size / 1024:.1f} KB")

            if not local_only and s3:
                with open(local_path, "rb") as f:
                    s3.put_object(
                        Bucket=settings.S3_BUCKET_NAME,
                        Key=f"backups/{backup_name}/{media_filename}",
                        Body=f.read(),
                        ContentType="application/gzip",
                    )
                self.stdout.write(self.style.SUCCESS(f"  Uploaded to S3: {backup_name}/{media_filename}"))

        except Exception as e:
            self.stderr.write(self.style.WARNING(f"Media backup failed: {e}"))

    def _cleanup_s3_backups(self, s3, retention_days):
        """Clean up old backups from S3."""
        self.stdout.write(f"Cleaning up S3 backups older than {retention_days} days...")

        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            # List all objects in backups/
            response = s3.list_objects_v2(
                Bucket=settings.S3_BUCKET_NAME,
                Prefix="backups/",
            )

            old_objects = []

            for obj in response.get("Contents", []):
                if obj["LastModified"].replace(tzinfo=None) < cutoff_date:
                    old_objects.append(obj["Key"])

            # Delete old objects
            for key in old_objects:
                s3.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
                self.stdout.write(f"  Deleted from S3: {key}")

            if old_objects:
                self.stdout.write(f"Deleted {len(old_objects)} old S3 file(s)")

        except Exception as e:
            self.stderr.write(self.style.WARNING(f"S3 cleanup warning: {e}"))

    def _cleanup_local_backups(self, backup_dir, retention_days):
        """Clean up old local backups."""
        self.stdout.write(f"Cleaning up local backups older than {retention_days} days...")

        cutoff_date = datetime.now() - timedelta(days=retention_days)
        deleted_count = 0

        for backup_subdir in backup_dir.glob("backup_*"):
            if not backup_subdir.is_dir():
                continue

            dir_mtime = datetime.fromtimestamp(backup_subdir.stat().st_mtime)
            if dir_mtime < cutoff_date:
                # Remove all files in directory
                for f in backup_subdir.iterdir():
                    f.unlink()
                backup_subdir.rmdir()
                deleted_count += 1
                self.stdout.write(f"  Deleted local: {backup_subdir.name}")

        if deleted_count:
            self.stdout.write(f"Deleted {deleted_count} old local backup(s)")
