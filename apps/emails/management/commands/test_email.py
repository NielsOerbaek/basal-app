from datetime import date, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.formats import date_format

import resend

from apps.emails.models import EmailTemplate, EmailType


class Command(BaseCommand):
    help = 'Test e-mail skabeloner og afsendelse'

    def add_arguments(self, parser):
        parser.add_argument(
            'email_type',
            choices=['signup_confirmation', 'course_reminder'],
            help='Type af e-mail skabelon at teste',
        )
        parser.add_argument(
            '--to',
            type=str,
            help='E-mail adresse at sende test til (udelad for kun at vise preview)',
        )
        parser.add_argument(
            '--participant-name',
            type=str,
            default='Test Deltager',
            help='Test deltager navn',
        )
        parser.add_argument(
            '--school-name',
            type=str,
            default='Test Skole',
            help='Test skole navn',
        )
        parser.add_argument(
            '--course-title',
            type=str,
            default='Introduktion til Basal - Test',
            help='Test kursus titel',
        )
        parser.add_argument(
            '--attachment',
            type=str,
            help='Sti til PDF fil at vedhæfte (simulerer kursusmateriale)',
        )

    def handle(self, *args, **options):
        email_type = options['email_type']
        recipient = options.get('to')

        # Get template
        try:
            template = EmailTemplate.objects.get(email_type=email_type)
        except EmailTemplate.DoesNotExist:
            self.stderr.write(self.style.ERROR(
                f'Skabelon "{email_type}" findes ikke. Kør migrations først.'
            ))
            return

        if not template.is_active:
            self.stdout.write(self.style.WARNING('Advarsel: Skabelonen er deaktiveret'))

        # Build test context
        test_date = date.today() + timedelta(days=14)
        context = {
            'participant_name': options['participant_name'],
            'participant_email': recipient or 'test@example.com',
            'participant_title': 'Lærer',
            'school_name': options['school_name'],
            'course_title': options['course_title'],
            'course_date': date_format(test_date, 'j. F Y'),
            'course_location': 'København',
        }

        # Render template
        from django.template import Template, Context
        subject = Template(template.subject).render(Context(context))
        body_html = Template(template.body_html).render(Context(context))

        # Show preview
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('E-MAIL PREVIEW'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'\nType: {template.get_email_type_display()}')
        self.stdout.write(f'Fra: {settings.DEFAULT_FROM_EMAIL}')
        self.stdout.write(f'Til: {recipient or "(ingen - kun preview)"}')
        self.stdout.write(f'\nEmne: {subject}')
        self.stdout.write('\n' + '-' * 60)
        self.stdout.write('Indhold (HTML):')
        self.stdout.write('-' * 60)
        self.stdout.write(body_html)
        self.stdout.write('-' * 60 + '\n')

        # Prepare attachments (simulating course materials)
        attachments = []
        attachment_path = options.get('attachment')
        if attachment_path:
            try:
                import os
                with open(attachment_path, 'rb') as f:
                    content = f.read()
                    attachments.append({
                        'filename': os.path.basename(attachment_path),
                        'content': list(content),
                    })
                self.stdout.write(self.style.SUCCESS(
                    f'Vedhæfter kursusmateriale: {os.path.basename(attachment_path)} ({len(content)} bytes)'
                ))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Kunne ikke læse fil: {e}'))
                return

        # Send if recipient provided
        if recipient:
            if not settings.RESEND_API_KEY:
                self.stderr.write(self.style.ERROR(
                    'RESEND_API_KEY er ikke konfigureret. '
                    'Tilføj den til .env for at sende e-mails.'
                ))
                return

            self.stdout.write(f'Sender test e-mail til {recipient}...')

            try:
                resend.api_key = settings.RESEND_API_KEY
                email_params = {
                    "from": settings.DEFAULT_FROM_EMAIL,
                    "to": [recipient],
                    "subject": f"[TEST] {subject}",
                    "html": body_html,
                }
                if attachments:
                    email_params["attachments"] = attachments

                result = resend.Emails.send(email_params)
                self.stdout.write(self.style.SUCCESS(f'E-mail sendt! ID: {result.get("id", "unknown")}'))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Fejl ved afsendelse: {e}'))
        else:
            self.stdout.write(self.style.WARNING(
                'Brug --to <email> for at sende en test e-mail'
            ))
