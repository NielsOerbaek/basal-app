from datetime import date, timedelta

from django.core.management.base import BaseCommand

from apps.courses.models import Course
from apps.emails.models import EmailLog, EmailType
from apps.emails.services import send_course_reminder


class Command(BaseCommand):
    help = "Send kursuspåmindelser til deltagere 14 dage før kursusstart"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Vis hvad der ville blive sendt uden at sende",
        )
        parser.add_argument(
            "--days-before",
            type=int,
            default=14,
            help="Antal dage før kursusstart (standard: 14)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        days_before = options["days_before"]

        target_date = date.today() + timedelta(days=days_before)

        # Find courses starting on target date
        courses = Course.objects.filter(start_date=target_date)

        if not courses.exists():
            self.stdout.write(f"Ingen kurser starter om {days_before} dage ({target_date})")
            return

        self.stdout.write(f"Finder kurser der starter {target_date} ({days_before} dage fra nu)...")

        total_sent = 0
        total_skipped = 0

        for course in courses:
            self.stdout.write(f"\nKursus: {course.display_name}")

            # Get signups with email addresses
            signups = course.signups.exclude(participant_email="")

            if not signups.exists():
                self.stdout.write("  Ingen tilmeldinger med e-mail")
                continue

            # Prepare attachments from course materials
            attachments = None
            if course.materials:
                try:
                    filename = course.materials.name.split("/")[-1]
                    with course.materials.open("rb") as f:
                        content = f.read()
                        attachments = [
                            {
                                "filename": filename,
                                "content": list(content),
                            }
                        ]
                    self.stdout.write(self.style.SUCCESS(f"  Kursusmateriale: {filename} ({len(content)} bytes)"))
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"  Kunne ikke læse kursusmateriale: {e}"))

            for signup in signups:
                # Check if reminder already sent
                already_sent = EmailLog.objects.filter(
                    email_type=EmailType.COURSE_REMINDER,
                    signup=signup,
                    success=True,
                ).exists()

                if already_sent:
                    self.stdout.write(f"  Allerede sendt til: {signup.participant_email}")
                    total_skipped += 1
                    continue

                if dry_run:
                    self.stdout.write(f"  [DRY-RUN] Ville sende til: {signup.participant_email}")
                    total_sent += 1
                else:
                    success = send_course_reminder(signup, attachments=attachments)
                    if success:
                        self.stdout.write(self.style.SUCCESS(f"  Sendt til: {signup.participant_email}"))
                        total_sent += 1
                    else:
                        self.stderr.write(self.style.ERROR(f"  Fejl ved afsendelse til: {signup.participant_email}"))

        self.stdout.write("")
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"[DRY-RUN] Ville sende {total_sent} e-mails, {total_skipped} allerede sendt")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Sendt {total_sent} e-mails, {total_skipped} sprunget over (allerede sendt)")
            )
