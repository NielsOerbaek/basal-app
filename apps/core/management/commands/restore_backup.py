import gzip
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Restore database and media files from a backup"

    def add_arguments(self, parser):
        parser.add_argument(
            "backup_name",
            type=str,
            help="Name of the backup to restore (e.g., backup_20241217_123456)",
        )
        parser.add_argument(
            "--backup-dir",
            type=str,
            default="/app/backups",
            help="Local backup directory (default: /app/backups)",
        )
        parser.add_argument(
            "--skip-pre-backup",
            action="store_true",
            help="Skip creating a backup before restoring (not recommended)",
        )
        parser.add_argument(
            "--skip-media",
            action="store_true",
            help="Skip restoring media files (database only)",
        )
        parser.add_argument(
            "--from-s3",
            action="store_true",
            help="Download backup from S3 if not available locally",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Skip confirmation prompt",
        )

    def handle(self, *args, **options):
        backup_name = options["backup_name"]
        backup_dir = Path(options["backup_dir"])
        skip_pre_backup = options["skip_pre_backup"]
        skip_media = options["skip_media"]
        from_s3 = options["from_s3"]
        confirmed = options["yes"]

        # Normalize backup name (allow with or without backup_ prefix)
        if not backup_name.startswith("backup_"):
            backup_name = f"backup_{backup_name}"

        local_backup_path = backup_dir / backup_name

        # Check if backup exists locally
        if not local_backup_path.exists():
            if from_s3:
                self.stdout.write("Backup not found locally, downloading from S3...")
                if not self._download_from_s3(backup_name, local_backup_path):
                    raise CommandError(f"Failed to download backup: {backup_name}")
            else:
                raise CommandError(f"Backup not found: {local_backup_path}\n" f"Use --from-s3 to download from S3")

        # Verify backup contents
        db_file = local_backup_path / "database.sql.gz"
        media_file = local_backup_path / "media.tar.gz"

        if not db_file.exists():
            raise CommandError(f"Database backup not found: {db_file}")

        has_media = media_file.exists()
        if not skip_media and not has_media:
            self.stdout.write(self.style.WARNING("No media backup found, skipping media restore"))
            skip_media = True

        # Confirmation prompt
        if not confirmed:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("=" * 60))
            self.stdout.write(self.style.WARNING("WARNING: This will OVERWRITE your current data!"))
            self.stdout.write(self.style.WARNING("=" * 60))
            self.stdout.write(f"Backup to restore: {backup_name}")
            self.stdout.write(f"  - Database: {db_file.stat().st_size / 1024:.1f} KB")
            if has_media and not skip_media:
                self.stdout.write(f"  - Media: {media_file.stat().st_size / 1024:.1f} KB")
            self.stdout.write("")

            response = input('Type "RESTORE" to confirm: ')
            if response != "RESTORE":
                self.stdout.write(self.style.ERROR("Restore cancelled"))
                return

        # Create pre-restore backup
        if not skip_pre_backup:
            self.stdout.write("")
            self.stdout.write("Creating pre-restore backup...")
            try:
                call_command("backup", "--backup-dir", str(backup_dir))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Pre-restore backup failed: {e}"))
                raise CommandError("Aborting restore due to backup failure")

        # Restore database
        self.stdout.write("")
        self.stdout.write(f"Restoring database from {backup_name}...")
        if not self._restore_database(db_file):
            raise CommandError("Database restore failed")

        # Restore media files
        if not skip_media and has_media:
            self.stdout.write(f"Restoring media files from {backup_name}...")
            if not self._restore_media(media_file):
                self.stderr.write(self.style.WARNING("Media restore failed, but database was restored"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Restore completed from: {backup_name}"))

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
        except Exception:
            return None

    def _download_from_s3(self, backup_name, local_path):
        """Download backup from S3."""
        s3 = self._get_s3_client()
        if not s3:
            self.stderr.write(self.style.ERROR("S3 not configured"))
            return False

        try:
            # List files in the backup directory
            response = s3.list_objects_v2(
                Bucket=settings.S3_BUCKET_NAME,
                Prefix=f"backups/{backup_name}/",
            )

            contents = response.get("Contents", [])
            if not contents:
                self.stderr.write(self.style.ERROR(f"Backup not found on S3: {backup_name}"))
                return False

            local_path.mkdir(parents=True, exist_ok=True)

            for obj in contents:
                key = obj["Key"]
                filename = key.split("/")[-1]
                if not filename:
                    continue

                self.stdout.write(f"  Downloading: {filename}")
                local_file = local_path / filename

                response = s3.get_object(
                    Bucket=settings.S3_BUCKET_NAME,
                    Key=key,
                )
                local_file.write_bytes(response["Body"].read())

            return True

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"S3 download failed: {e}"))
            return False

    def _restore_database(self, db_file):
        """Restore PostgreSQL database from backup."""
        import dj_database_url

        db_config = dj_database_url.config()

        if not db_config:
            self.stderr.write(self.style.ERROR("DATABASE_URL not configured"))
            return False

        env = os.environ.copy()
        env["PGPASSWORD"] = db_config.get("PASSWORD", "")

        db_host = db_config.get("HOST", "localhost")
        db_port = str(db_config.get("PORT", 5432))
        db_user = db_config.get("USER", "postgres")
        db_name = db_config.get("NAME", "basal")

        try:
            # Decompress the backup
            self.stdout.write("  Decompressing backup...")
            with gzip.open(db_file, "rb") as f:
                sql_data = f.read()

            # Drop and recreate the database
            # First, terminate existing connections
            self.stdout.write("  Terminating existing connections...")
            terminate_sql = f"""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = '{db_name}' AND pid <> pg_backend_pid();
            """

            subprocess.run(
                ["psql", "-h", db_host, "-p", db_port, "-U", db_user, "-d", "postgres", "-c", terminate_sql],
                env=env,
                capture_output=True,
            )

            # Drop and recreate database
            self.stdout.write("  Dropping database...")
            subprocess.run(
                ["dropdb", "-h", db_host, "-p", db_port, "-U", db_user, "--if-exists", db_name],
                env=env,
                capture_output=True,
                check=True,
            )

            self.stdout.write("  Creating database...")
            subprocess.run(
                ["createdb", "-h", db_host, "-p", db_port, "-U", db_user, db_name],
                env=env,
                capture_output=True,
                check=True,
            )

            # Restore the backup
            self.stdout.write("  Restoring data...")
            result = subprocess.run(
                ["psql", "-h", db_host, "-p", db_port, "-U", db_user, "-d", db_name],
                env=env,
                input=sql_data,
                capture_output=True,
            )

            if result.returncode != 0:
                # psql may return non-zero for warnings, check stderr for actual errors
                stderr = result.stderr.decode()
                if "ERROR" in stderr:
                    self.stderr.write(self.style.ERROR(f"Restore errors: {stderr}"))
                    return False

            self.stdout.write(self.style.SUCCESS("  Database restored successfully"))
            return True

        except subprocess.CalledProcessError as e:
            self.stderr.write(self.style.ERROR(f"Database restore failed: {e.stderr.decode()}"))
            return False
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Database restore failed: {e}"))
            return False

    def _restore_media(self, media_file):
        """Restore media files from backup."""
        media_root = Path(settings.MEDIA_ROOT)

        try:
            # Create a backup of current media (just rename)
            if media_root.exists():
                backup_media = media_root.parent / f"{media_root.name}_old"
                if backup_media.exists():
                    shutil.rmtree(backup_media)
                media_root.rename(backup_media)
                self.stdout.write("  Backed up existing media directory")

            # Extract the media archive
            self.stdout.write("  Extracting media files...")
            media_root.parent.mkdir(parents=True, exist_ok=True)

            with tarfile.open(media_file, "r:gz") as tar:
                tar.extractall(media_root.parent)

            # Clean up old media backup
            backup_media = media_root.parent / f"{media_root.name}_old"
            if backup_media.exists():
                shutil.rmtree(backup_media)

            self.stdout.write(self.style.SUCCESS("  Media files restored successfully"))
            return True

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Media restore failed: {e}"))
            # Try to restore old media if available
            backup_media = media_root.parent / f"{media_root.name}_old"
            if backup_media.exists():
                if media_root.exists():
                    shutil.rmtree(media_root)
                backup_media.rename(media_root)
                self.stdout.write("  Restored original media directory")
            return False
