import random
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.contacts.models import ContactTime
from apps.courses.models import AttendanceStatus, Course, CourseSignUp
from apps.schools.models import School


class Command(BaseCommand):
    help = 'Opretter demo data til udvikling og test'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Slet eksisterende demo data før oprettelse',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Sletter eksisterende data...')
            CourseSignUp.objects.all().delete()
            ContactTime.objects.all().delete()
            Course.objects.all().delete()
            School.objects.filter(is_active=True).update(is_active=False)
            School.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Eksisterende data slettet'))

        self.stdout.write('Opretter demo data...')

        # Create schools
        schools = self.create_schools()
        self.stdout.write(self.style.SUCCESS(f'  {len(schools)} skoler oprettet'))

        # Create courses
        courses = self.create_courses()
        self.stdout.write(self.style.SUCCESS(f'  {len(courses)} kurser oprettet'))

        # Create signups
        signups = self.create_signups(schools, courses)
        self.stdout.write(self.style.SUCCESS(f'  {len(signups)} tilmeldinger oprettet'))

        # Create contact history (henvendelser)
        contacts = self.create_contacts(schools)
        self.stdout.write(self.style.SUCCESS(f'  {len(contacts)} henvendelser oprettet'))

        self.stdout.write(self.style.SUCCESS('\nDemo data oprettet!'))

    def create_schools(self):
        schools_data = [
            {
                'name': 'Aarhus Gymnasium',
                'location': 'Aarhus C',
                'contact_name': 'Lars Pedersen',
                'contact_email': 'lars.pedersen@aarhus-gym.dk',
                'contact_phone': '86 12 34 56',
            },
            {
                'name': 'Odense Tekniske Skole',
                'location': 'Odense SØ',
                'contact_name': 'Mette Hansen',
                'contact_email': 'mette.hansen@odense-tek.dk',
                'contact_phone': '65 98 76 54',
            },
            {
                'name': 'Aalborg Handelsskole',
                'location': 'Aalborg Ø',
                'contact_name': 'Søren Nielsen',
                'contact_email': 'soren.nielsen@aalborg-handel.dk',
                'contact_phone': '98 11 22 33',
            },
            {
                'name': 'Roskilde Katedralskole',
                'location': 'Roskilde',
                'contact_name': 'Anne Christensen',
                'contact_email': 'anne.c@roskilde-kat.dk',
                'contact_phone': '46 35 12 00',
            },
            {
                'name': 'Esbjerg Seminarium',
                'location': 'Esbjerg V',
                'contact_name': 'Peter Mortensen',
                'contact_email': 'pm@esbjerg-sem.dk',
                'contact_phone': '75 45 67 89',
            },
            {
                'name': 'Københavns Professionshøjskole',
                'location': 'København N',
                'contact_name': 'Kirsten Larsen',
                'contact_email': 'kila@kp.dk',
                'contact_phone': '72 48 75 00',
            },
            {
                'name': 'Vejle Handelsskole',
                'location': 'Vejle',
                'contact_name': 'Michael Jensen',
                'contact_email': 'mj@vejle-handel.dk',
                'contact_phone': '76 82 00 00',
            },
            {
                'name': 'Frederiksberg HF',
                'location': 'Frederiksberg',
                'contact_name': 'Louise Andersen',
                'contact_email': 'louise@frb-hf.dk',
                'contact_phone': '38 14 22 33',
            },
            {
                'name': 'Herning Gymnasium',
                'location': 'Herning',
                'contact_name': 'Thomas Rasmussen',
                'contact_email': 'tr@herning-gym.dk',
                'contact_phone': '97 12 34 56',
            },
            {
                'name': 'Svendborg Erhvervsskole',
                'location': 'Svendborg',
                'contact_name': 'Camilla Olsen',
                'contact_email': 'co@svendborg-erhv.dk',
                'contact_phone': '62 21 00 00',
            },
            {
                'name': 'Viborg Katedralskole',
                'location': 'Viborg',
                'contact_name': 'Henrik Thomsen',
                'contact_email': 'ht@viborg-kat.dk',
                'contact_phone': '86 62 45 00',
            },
            {
                'name': 'Næstved Gymnasium',
                'location': 'Næstved',
                'contact_name': 'Marie Kjær',
                'contact_email': 'mk@naestved-gym.dk',
                'contact_phone': '55 77 15 00',
            },
        ]

        schools = []
        for data in schools_data:
            school, created = School.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            if created:
                schools.append(school)
        return schools

    def create_courses(self):
        today = date.today()
        courses_data = [
            # Past courses
            {
                'title': 'Introduktion til digital undervisning',
                'start_date': today - timedelta(days=60),
                'end_date': today - timedelta(days=59),
                'location': 'København',
                'capacity': 25,
                'is_published': True,
                'comment': 'Grundlæggende kursus i digitale værktøjer',
            },
            {
                'title': 'Inkluderende undervisning i praksis',
                'start_date': today - timedelta(days=30),
                'end_date': today - timedelta(days=28),
                'location': 'Aarhus',
                'capacity': 20,
                'is_published': True,
                'comment': 'Fokus på differentieret undervisning',
            },
            # Current/upcoming courses
            {
                'title': 'Feedback og evaluering',
                'start_date': today + timedelta(days=7),
                'end_date': today + timedelta(days=7),
                'location': 'Odense',
                'capacity': 30,
                'is_published': True,
                'comment': 'En-dags workshop om effektiv feedback',
            },
            {
                'title': 'Klasseledelse for nye lærere',
                'start_date': today + timedelta(days=14),
                'end_date': today + timedelta(days=15),
                'location': 'København',
                'capacity': 25,
                'is_published': True,
                'comment': 'To-dages intensivt kursus',
            },
            {
                'title': 'Digital dannelse og kildekritik',
                'start_date': today + timedelta(days=21),
                'end_date': today + timedelta(days=21),
                'location': 'Aalborg',
                'capacity': 35,
                'is_published': True,
            },
            {
                'title': 'Projektbaseret læring',
                'start_date': today + timedelta(days=30),
                'end_date': today + timedelta(days=32),
                'location': 'Vejle',
                'capacity': 20,
                'is_published': True,
                'comment': 'Tre-dages kursus med praktiske øvelser',
            },
            {
                'title': 'Trivsel og motivation i klasserummet',
                'start_date': today + timedelta(days=45),
                'end_date': today + timedelta(days=45),
                'location': 'Roskilde',
                'capacity': 40,
                'is_published': True,
            },
            # Unpublished course
            {
                'title': 'Avanceret pædagogik (under udvikling)',
                'start_date': today + timedelta(days=90),
                'end_date': today + timedelta(days=92),
                'location': 'København',
                'capacity': 15,
                'is_published': False,
                'comment': 'Kursus under udvikling - ikke offentliggjort endnu',
            },
        ]

        courses = []
        for data in courses_data:
            course, created = Course.objects.get_or_create(
                title=data['title'],
                start_date=data['start_date'],
                defaults=data
            )
            if created:
                courses.append(course)
        return courses

    def create_signups(self, schools, courses):
        # Get all schools (including existing ones)
        all_schools = list(School.objects.active())
        all_courses = list(Course.objects.all())

        if not all_schools or not all_courses:
            return []

        first_names = [
            'Anders', 'Birgitte', 'Christian', 'Dorte', 'Erik',
            'Fie', 'Gustav', 'Hanne', 'Ivan', 'Julie',
            'Klaus', 'Lene', 'Martin', 'Nanna', 'Ole',
            'Pia', 'Rasmus', 'Sara', 'Torben', 'Ulla',
        ]
        last_names = [
            'Jensen', 'Nielsen', 'Hansen', 'Pedersen', 'Andersen',
            'Christensen', 'Larsen', 'Sørensen', 'Rasmussen', 'Thomsen',
        ]
        titles = [
            'Lærer', 'Lektor', 'Underviser', 'Pædagog',
            'Adjunkt', 'Fagkoordinator', 'Studievejleder',
        ]

        signups = []
        for course in all_courses:
            # Random number of signups per course (3-15)
            num_signups = random.randint(3, min(15, course.capacity))
            selected_schools = random.sample(all_schools, min(num_signups, len(all_schools)))

            for school in selected_schools:
                first = random.choice(first_names)
                last = random.choice(last_names)
                name = f'{first} {last}'

                try:
                    signup = CourseSignUp.objects.create(
                        school=school,
                        course=course,
                        participant_name=name,
                        participant_title=random.choice(titles),
                        attendance=self.get_attendance_for_course(course),
                    )
                    signups.append(signup)
                except Exception:
                    # Skip if unique constraint violation
                    pass

        return signups

    def get_attendance_for_course(self, course):
        """Return appropriate attendance status based on course date."""
        today = date.today()
        if course.end_date < today:
            # Past course - assign random attendance
            return random.choices(
                [AttendanceStatus.PRESENT, AttendanceStatus.ABSENT],
                weights=[0.85, 0.15]
            )[0]
        else:
            # Future course - unmarked
            return AttendanceStatus.UNMARKED

    def create_contacts(self, schools):
        all_schools = list(School.objects.active())
        if not all_schools:
            return []

        # Get admin user for created_by
        try:
            admin_user = User.objects.get(username='admin')
        except User.DoesNotExist:
            admin_user = None

        comments = [
            'Talte med kontaktperson om kommende kurser. God interesse.',
            'Sendt information om efterårssæsonen.',
            'Opfølgning på tidligere tilmelding. Ønsker flere pladser.',
            'Koordineret praktiske detaljer omkring transport.',
            'Diskuterede muligheder for skræddersyet kursusforløb.',
            'Modtaget feedback fra tidligere kursus. Meget positive tilbagemeldinger.',
            'Aftalt at sende opdateret kursusoversigt.',
            'Gennemgået tilmeldingsprocedure med ny kontaktperson.',
            'Bekræftet deltagelse i kommende kursus.',
            'Drøftet behov for særlige tilpasninger.',
        ]

        contacts = []
        for school in all_schools:
            # 1-4 contact entries per school
            num_contacts = random.randint(1, 4)
            for i in range(num_contacts):
                days_ago = random.randint(1, 180)
                contacted_at = timezone.now() - timedelta(days=days_ago)

                contact = ContactTime.objects.create(
                    school=school,
                    created_by=admin_user,
                    contacted_at=contacted_at,
                    comment=random.choice(comments),
                )
                contacts.append(contact)

        return contacts
