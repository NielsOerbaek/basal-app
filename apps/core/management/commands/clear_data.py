from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Sletter alle skoler, kurser og relaterede data mens brugere bevares'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Bekræft sletning (påkrævet)',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.ERROR(
                'Brug --confirm for at bekræfte sletning af alle data'
            ))
            return

        self.stdout.write('Sletter alle data (bevarer brugere)...')

        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                TRUNCATE TABLE
                    audit_activitylog,
                    courses_coursesignup,
                    contacts_contacttime,
                    courses_course,
                    schools_schoolcomment,
                    schools_person,
                    schools_seatpurchase,
                    schools_invoice,
                    schools_schoolyearenrollment,
                    schools_school
                RESTART IDENTITY CASCADE
            """)

        self.stdout.write(self.style.SUCCESS('Alle data slettet (brugere bevaret)'))
