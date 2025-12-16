import random
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.contacts.models import ContactTime
from apps.courses.models import AttendanceStatus, Course, CourseSignUp
from apps.schools.models import School, SeatPurchase


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
            SeatPurchase.objects.all().delete()
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

        # Create signups (respecting seat limits)
        signups = self.create_signups(schools, courses)
        self.stdout.write(self.style.SUCCESS(f'  {len(signups)} tilmeldinger oprettet'))

        # Create contact history (henvendelser)
        contacts = self.create_contacts(schools)
        self.stdout.write(self.style.SUCCESS(f'  {len(contacts)} henvendelser oprettet'))

        self.stdout.write(self.style.SUCCESS('\nDemo data oprettet!'))

    def create_schools(self):
        schools_data = [
            {
                'name': 'Sønderbro Skole',
                'location': 'Amagerbrogade 45, 2300 København S',
                'contact_name': 'Lars Pedersen',
                'contact_email': 'lp@sonderbro-skole.dk',
                'contact_phone': '32 54 12 34',
            },
            {
                'name': 'Vesterbro Skole',
                'location': 'Vestergade 12, 1456 København V',
                'contact_name': 'Mette Hansen',
                'contact_email': 'mh@vesterbro-skole.dk',
                'contact_phone': '33 21 45 67',
            },
            {
                'name': 'Hasle Skole',
                'location': 'Haslevej 100, 8210 Aarhus V',
                'contact_name': 'Søren Nielsen',
                'contact_email': 'sn@hasle-skole.dk',
                'contact_phone': '86 15 23 45',
            },
            {
                'name': 'Munkebjerg Skole',
                'location': 'Munkebjergvej 80, 5230 Odense M',
                'contact_name': 'Anne Christensen',
                'contact_email': 'ac@munkebjerg-skole.dk',
                'contact_phone': '65 91 23 45',
            },
            {
                'name': 'Nørre Boulevard Skole',
                'location': 'Nørre Boulevard 5, 9000 Aalborg',
                'contact_name': 'Peter Mortensen',
                'contact_email': 'pm@nb-skole.dk',
                'contact_phone': '98 12 34 56',
            },
            {
                'name': 'Bakkeskolen',
                'location': 'Bakkedraget 22, 4000 Roskilde',
                'contact_name': 'Kirsten Larsen',
                'contact_email': 'kl@bakkeskolen.dk',
                'contact_phone': '46 35 12 00',
            },
            {
                'name': 'Strandskolen',
                'location': 'Strandvejen 150, 6700 Esbjerg',
                'contact_name': 'Michael Jensen',
                'contact_email': 'mj@strandskolen.dk',
                'contact_phone': '75 12 34 56',
            },
            {
                'name': 'Engdalskolen',
                'location': 'Engdalsvej 3, 8660 Skanderborg',
                'contact_name': 'Louise Andersen',
                'contact_email': 'la@engdalskolen.dk',
                'contact_phone': '86 52 12 34',
            },
            {
                'name': 'Skovvangskolen',
                'location': 'Skovvangen 10, 7400 Herning',
                'contact_name': 'Thomas Rasmussen',
                'contact_email': 'tr@skovvangskolen.dk',
                'contact_phone': '97 12 34 56',
            },
            {
                'name': 'Østervangskolen',
                'location': 'Østervang 25, 5700 Svendborg',
                'contact_name': 'Camilla Olsen',
                'contact_email': 'co@ostervangskolen.dk',
                'contact_phone': '62 21 00 00',
            },
            {
                'name': 'Nordvestskolen',
                'location': 'Nordvestgade 8, 8800 Viborg',
                'contact_name': 'Henrik Thomsen',
                'contact_email': 'ht@nordvestskolen.dk',
                'contact_phone': '86 62 45 00',
            },
            {
                'name': 'Kildeskovskolen',
                'location': 'Kildeskovvej 15, 4700 Næstved',
                'contact_name': 'Marie Kjær',
                'contact_email': 'mk@kildeskovskolen.dk',
                'contact_phone': '55 77 15 00',
            },
        ]

        schools = []
        today = date.today()
        for i, data in enumerate(schools_data):
            # Most schools enrolled, some recently, some over a year ago
            if i < 4:
                # Enrolled over a year ago (has forankringsplads)
                data['enrolled_at'] = today - timedelta(days=random.randint(400, 800))
            elif i < 10:
                # Enrolled within the last year
                data['enrolled_at'] = today - timedelta(days=random.randint(30, 300))
            else:
                # Not enrolled yet
                data['enrolled_at'] = None

            school, created = School.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            if created:
                schools.append(school)

        # Add some seat purchases for a few schools
        enrolled_schools = [s for s in schools if s.enrolled_at]
        for school in random.sample(enrolled_schools, min(3, len(enrolled_schools))):
            SeatPurchase.objects.create(
                school=school,
                seats=random.choice([2, 3, 5]),
                purchased_at=date.today() - timedelta(days=random.randint(10, 100)),
                notes='Ekstra pladser købt'
            )

        return schools

    def create_courses(self):
        today = date.today()

        # Generate month names for course titles
        months = [
            'Januar', 'Februar', 'Marts', 'April', 'Maj', 'Juni',
            'Juli', 'August', 'September', 'Oktober', 'November', 'December'
        ]

        def get_month_name(d):
            return months[d.month - 1]

        courses_data = [
            # Past courses
            {
                'title': f'Introduktion til Basal - {get_month_name(today - timedelta(days=60))}',
                'start_date': today - timedelta(days=60),
                'end_date': today - timedelta(days=60),
                'location': 'København',
                'capacity': 25,
                'is_published': True,
                'comment': 'Grundlæggende introduktion til Basal-metoden',
            },
            {
                'title': f'Introduktion til Basal - {get_month_name(today - timedelta(days=30))}',
                'start_date': today - timedelta(days=30),
                'end_date': today - timedelta(days=30),
                'location': 'Aarhus',
                'capacity': 20,
                'is_published': True,
                'comment': 'Grundlæggende introduktion til Basal-metoden',
            },
            # Upcoming courses
            {
                'title': f'Introduktion til Basal - {get_month_name(today + timedelta(days=14))}',
                'start_date': today + timedelta(days=14),
                'end_date': today + timedelta(days=14),
                'location': 'Odense',
                'capacity': 30,
                'is_published': True,
                'comment': 'Grundlæggende introduktion til Basal-metoden',
            },
            {
                'title': f'Basal for skoleledere - {get_month_name(today + timedelta(days=21))}',
                'start_date': today + timedelta(days=21),
                'end_date': today + timedelta(days=21),
                'location': 'København',
                'capacity': 20,
                'is_published': True,
                'comment': 'Kursus rettet mod skoleledere og mellemledere',
            },
            {
                'title': f'Basal opfølgning - {get_month_name(today + timedelta(days=35))}',
                'start_date': today + timedelta(days=35),
                'end_date': today + timedelta(days=35),
                'location': 'Aalborg',
                'capacity': 25,
                'is_published': True,
                'comment': 'Opfølgningskursus for deltagere der har taget introduktionen',
            },
            {
                'title': f'Introduktion til Basal - {get_month_name(today + timedelta(days=45))}',
                'start_date': today + timedelta(days=45),
                'end_date': today + timedelta(days=45),
                'location': 'Vejle',
                'capacity': 25,
                'is_published': True,
            },
            {
                'title': f'Basal Forankring - {get_month_name(today + timedelta(days=60))}',
                'start_date': today + timedelta(days=60),
                'end_date': today + timedelta(days=61),
                'location': 'Roskilde',
                'capacity': 15,
                'is_published': True,
                'comment': 'To-dages forankringskursus for nye lærere',
            },
            # Unpublished course
            {
                'title': f'Introduktion til Basal - {get_month_name(today + timedelta(days=90))}',
                'start_date': today + timedelta(days=90),
                'end_date': today + timedelta(days=90),
                'location': 'København',
                'capacity': 30,
                'is_published': False,
                'comment': 'Endnu ikke offentliggjort',
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
        # Get all enrolled schools (they have seats)
        enrolled_schools = list(School.objects.active().exclude(enrolled_at__isnull=True))
        all_courses = list(Course.objects.all())

        if not enrolled_schools or not all_courses:
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
            'Lærer',
            'Lærer',
            'Lærer',
            'Lærer',
            'Indskolingslærer',
            'Mellemtrinslærer',
            'Udskolingslærer',
            'Skoleleder',
            'Viceskoleleder',
            'Afdelingsleder',
        ]

        signups = []

        # Track remaining seats per school (all signups count against seats)
        school_remaining_seats = {s.pk: s.total_seats for s in enrolled_schools}

        for course in all_courses:
            # Random number of signups per course
            num_signups = random.randint(0, min(5, course.capacity))

            # Shuffle schools for random selection
            shuffled_schools = enrolled_schools.copy()
            random.shuffle(shuffled_schools)

            signups_for_course = 0
            for school in shuffled_schools:
                if signups_for_course >= num_signups:
                    break

                # Check seat availability
                if school_remaining_seats.get(school.pk, 0) <= 0:
                    continue

                first = random.choice(first_names)
                last = random.choice(last_names)
                name = f'{first} {last}'
                # Generate email from name and school domain
                email_name = f'{first.lower()}.{last.lower()}'
                school_domain = school.contact_email.split('@')[1] if '@' in school.contact_email else 'skole.dk'
                email = f'{email_name}@{school_domain}'

                try:
                    signup = CourseSignUp.objects.create(
                        school=school,
                        course=course,
                        participant_name=name,
                        participant_email=email,
                        participant_title=random.choice(titles),
                        attendance=self.get_attendance_for_course(course),
                    )
                    signups.append(signup)
                    signups_for_course += 1
                    school_remaining_seats[school.pk] -= 1
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

        # Create or get staff users for contacts
        esther, _ = User.objects.get_or_create(
            username='esther',
            defaults={
                'first_name': 'Esther',
                'last_name': 'Chemnitz',
                'email': 'esther@basal.dk',
                'is_staff': True,
            }
        )
        caroline, _ = User.objects.get_or_create(
            username='caroline',
            defaults={
                'first_name': 'Caroline',
                'last_name': 'Buskov',
                'email': 'caroline@basal.dk',
                'is_staff': True,
            }
        )
        staff_users = [esther, caroline]

        comments = [
            'Talte med skoleleder om tilmelding til Basal. God interesse.',
            'Sendt information om kommende kurser.',
            'Opfølgning på tidligere kursusdeltagelse. Ønsker flere pladser.',
            'Koordineret praktiske detaljer omkring kursusdeltagelse.',
            'Diskuterede muligheder for forankringskursus.',
            'Modtaget feedback fra tidligere kursus. Meget positive tilbagemeldinger.',
            'Aftalt at sende opdateret kursusoversigt til lærerne.',
            'Gennemgået tilmeldingsprocedure med ny kontaktperson.',
            'Bekræftet deltagelse i kommende introduktionskursus.',
            'Drøftet behov for ekstra pladser til næste skoleår.',
        ]

        contacts = []
        for school in all_schools:
            # 1-4 contact entries per school
            num_contacts = random.randint(1, 4)
            for i in range(num_contacts):
                days_ago = random.randint(1, 180)
                contacted_date = (timezone.now() - timedelta(days=days_ago)).date()
                # Some contacts have time, some don't
                contacted_time = None
                if random.random() > 0.3:
                    contacted_time = timezone.now().time().replace(
                        hour=random.randint(8, 17),
                        minute=random.choice([0, 15, 30, 45])
                    )

                contact = ContactTime.objects.create(
                    school=school,
                    created_by=random.choice(staff_users),
                    contacted_date=contacted_date,
                    contacted_time=contacted_time,
                    inbound=random.choice([True, False]),
                    comment=random.choice(comments),
                )
                contacts.append(contact)

        return contacts
