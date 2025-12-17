import gzip
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Backup database to Backblaze B2 or local storage'

    def add_arguments(self, parser):
        parser.add_argument(
            '--retention-days',
            type=int,
            default=30,
            help='Number of days to keep backups (default: 30)',
        )
        parser.add_argument(
            '--local-only',
            action='store_true',
            help='Store backup locally only (skip B2 upload)',
        )
        parser.add_argument(
            '--backup-dir',
            type=str,
            default='/app/backups',
            help='Local backup directory (default: /app/backups)',
        )

    def handle(self, *args, **options):
        local_only = options['local_only']
        backup_dir = Path(options['backup_dir'])

        # Check B2 settings if not local-only
        if not local_only:
            required_settings = [
                'B2_KEY_ID',
                'B2_APPLICATION_KEY',
                'B2_BUCKET_NAME',
                'B2_ENDPOINT',
            ]
            missing = [s for s in required_settings if not getattr(settings, s, None)]
            if missing:
                self.stdout.write(self.style.WARNING(
                    f'B2 settings missing ({", ".join(missing)}), using local-only mode'
                ))
                local_only = True

        # Get database URL components
        import dj_database_url
        db_config = dj_database_url.config()

        if not db_config:
            self.stderr.write(self.style.ERROR('DATABASE_URL not configured'))
            return

        # Create backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'basal_backup_{timestamp}.sql.gz'

        self.stdout.write(f'Creating backup: {backup_filename}')

        # Build pg_dump command
        env = os.environ.copy()
        env['PGPASSWORD'] = db_config.get('PASSWORD', '')

        pg_dump_cmd = [
            'pg_dump',
            '-h', db_config.get('HOST', 'localhost'),
            '-p', str(db_config.get('PORT', 5432)),
            '-U', db_config.get('USER', 'postgres'),
            '-d', db_config.get('NAME', 'basal'),
            '--no-owner',
            '--no-acl',
        ]

        try:
            # Run pg_dump and compress
            result = subprocess.run(
                pg_dump_cmd,
                env=env,
                capture_output=True,
                check=True,
            )

            compressed_data = gzip.compress(result.stdout)
            backup_size = len(compressed_data)

            self.stdout.write(f'Backup size: {backup_size / 1024:.1f} KB')

        except subprocess.CalledProcessError as e:
            self.stderr.write(self.style.ERROR(f'pg_dump failed: {e.stderr.decode()}'))
            return
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(
                'pg_dump not found. Install postgresql-client.'
            ))
            return

        # Save locally
        backup_dir.mkdir(parents=True, exist_ok=True)
        local_path = backup_dir / backup_filename
        local_path.write_bytes(compressed_data)
        self.stdout.write(self.style.SUCCESS(f'Local backup saved: {local_path}'))

        # Upload to B2 if configured
        if not local_only:
            self.stdout.write('Uploading to Backblaze B2...')

            try:
                import boto3
                from botocore.config import Config

                s3 = boto3.client(
                    's3',
                    endpoint_url=settings.B2_ENDPOINT,
                    aws_access_key_id=settings.B2_KEY_ID,
                    aws_secret_access_key=settings.B2_APPLICATION_KEY,
                    config=Config(
                        signature_version='s3v4',
                        retries={'max_attempts': 3, 'mode': 'standard'},
                    ),
                )

                s3.put_object(
                    Bucket=settings.B2_BUCKET_NAME,
                    Key=f'backups/{backup_filename}',
                    Body=compressed_data,
                    ContentType='application/gzip',
                )

                self.stdout.write(self.style.SUCCESS(
                    f'B2 backup uploaded: backups/{backup_filename}'
                ))

                # Clean up old B2 backups
                self._cleanup_b2_backups(s3, options['retention_days'])

            except Exception as e:
                self.stderr.write(self.style.WARNING(f'B2 upload failed: {e}'))
                self.stdout.write('Local backup is still available.')

        # Clean up old local backups
        self._cleanup_local_backups(backup_dir, options['retention_days'])

        self.stdout.write(self.style.SUCCESS('Backup completed successfully!'))

    def _cleanup_b2_backups(self, s3, retention_days):
        """Clean up old backups from B2."""
        self.stdout.write(f'Cleaning up B2 backups older than {retention_days} days...')

        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            response = s3.list_objects_v2(
                Bucket=settings.B2_BUCKET_NAME,
                Prefix='backups/',
            )

            deleted_count = 0
            for obj in response.get('Contents', []):
                if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                    s3.delete_object(
                        Bucket=settings.B2_BUCKET_NAME,
                        Key=obj['Key'],
                    )
                    deleted_count += 1
                    self.stdout.write(f'  Deleted from B2: {obj["Key"]}')

            if deleted_count:
                self.stdout.write(f'Deleted {deleted_count} old B2 backup(s)')

        except Exception as e:
            self.stderr.write(self.style.WARNING(f'B2 cleanup warning: {e}'))

    def _cleanup_local_backups(self, backup_dir, retention_days):
        """Clean up old local backups."""
        self.stdout.write(f'Cleaning up local backups older than {retention_days} days...')

        cutoff_date = datetime.now() - timedelta(days=retention_days)
        deleted_count = 0

        for backup_file in backup_dir.glob('basal_backup_*.sql.gz'):
            file_mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
            if file_mtime < cutoff_date:
                backup_file.unlink()
                deleted_count += 1
                self.stdout.write(f'  Deleted local: {backup_file.name}')

        if deleted_count:
            self.stdout.write(f'Deleted {deleted_count} old local backup(s)')
