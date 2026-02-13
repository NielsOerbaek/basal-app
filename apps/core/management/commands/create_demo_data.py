import random
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.audit.models import ActivityLog
from apps.contacts.models import ContactTime
from apps.courses.models import AttendanceStatus, Course, CourseSignUp
from apps.schools.models import Person, PersonRole, School, SchoolComment


class Command(BaseCommand):
    help = "Opretter demo data til udvikling og test"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Slet eksisterende demo data før oprettelse",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Sletter eksisterende data...")
            # Delete in correct order to handle foreign key constraints
            ActivityLog.objects.all().delete()
            CourseSignUp.objects.all().delete()
            ContactTime.objects.all().delete()
            Course.objects.all().delete()
            SchoolComment.objects.all().delete()
            Person.objects.all().delete()
            from apps.schools.models import Invoice

            Invoice.objects.all().delete()
            School.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Eksisterende data slettet"))

        self.stdout.write("Opretter demo data...")

        # Create admin user
        admin = self.create_admin_user()
        if admin:
            self.stdout.write(self.style.SUCCESS("  Admin bruger oprettet (admin/admin)"))

        # Create schools
        schools = self.create_schools()
        self.stdout.write(self.style.SUCCESS(f"  {len(schools)} skoler oprettet"))

        # Create courses
        courses = self.create_courses()
        self.stdout.write(self.style.SUCCESS(f"  {len(courses)} kurser oprettet"))

        # Create signups (respecting seat limits)
        signups = self.create_signups(schools, courses)
        self.stdout.write(self.style.SUCCESS(f"  {len(signups)} tilmeldinger oprettet"))

        # Create contact history (henvendelser)
        contacts = self.create_contacts(schools)
        self.stdout.write(self.style.SUCCESS(f"  {len(contacts)} henvendelser oprettet"))

        self.stdout.write(self.style.SUCCESS("\nDemo data oprettet!"))

    def create_admin_user(self):
        """Create admin superuser for development."""
        from django.contrib.auth.hashers import make_password

        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@example.com",
                "first_name": "Admin",
                "last_name": "User",
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
                "password": make_password("admin"),
            },
        )
        return admin if created else None

    def create_schools(self):
        schools_data = [
            {
                "name": "Sønderbro Skole",
                "adresse": "Amagerbrogade 45, 2300 København S",
                "kommune": "Københavns Kommune",
                "contact_name": "Lars Pedersen",
                "contact_email": "lp@sonderbro-skole.dk",
                "contact_phone": "32 54 12 34",
                "contact_role": PersonRole.KOORDINATOR,
            },
            {
                "name": "Vesterbro Skole",
                "adresse": "Vestergade 12, 1456 København V",
                "kommune": "Københavns Kommune",
                "contact_name": "Mette Hansen",
                "contact_email": "mh@vesterbro-skole.dk",
                "contact_phone": "33 21 45 67",
                "contact_role": PersonRole.SKOLELEDER,
            },
            {
                "name": "Hasle Skole",
                "adresse": "Haslevej 100, 8210 Aarhus V",
                "kommune": "Aarhus Kommune",
                "contact_name": "Søren Nielsen",
                "contact_email": "sn@hasle-skole.dk",
                "contact_phone": "86 15 23 45",
                "contact_role": PersonRole.KOORDINATOR,
            },
            {
                "name": "Munkebjerg Skole",
                "adresse": "Munkebjergvej 80, 5230 Odense M",
                "kommune": "Odense Kommune",
                "contact_name": "Anne Christensen",
                "contact_email": "ac@munkebjerg-skole.dk",
                "contact_phone": "65 91 23 45",
                "contact_role": PersonRole.UDSKOLINGSLEDER,
            },
            {
                "name": "Nørre Boulevard Skole",
                "adresse": "Nørre Boulevard 5, 9000 Aalborg",
                "kommune": "Aalborg Kommune",
                "contact_name": "Peter Mortensen",
                "contact_email": "pm@nb-skole.dk",
                "contact_phone": "98 12 34 56",
                "contact_role": PersonRole.KOORDINATOR,
            },
            {
                "name": "Bakkeskolen",
                "adresse": "Bakkedraget 22, 4000 Roskilde",
                "kommune": "Roskilde Kommune",
                "contact_name": "Kirsten Larsen",
                "contact_email": "kl@bakkeskolen.dk",
                "contact_phone": "46 35 12 00",
                "contact_role": PersonRole.KOORDINATOR,
            },
            {
                "name": "Strandskolen",
                "adresse": "Strandvejen 150, 6700 Esbjerg",
                "kommune": "Esbjerg Kommune",
                "contact_name": "Michael Jensen",
                "contact_email": "mj@strandskolen.dk",
                "contact_phone": "75 12 34 56",
                "contact_role": PersonRole.SKOLELEDER,
            },
            {
                "name": "Engdalskolen",
                "adresse": "Engdalsvej 3, 8660 Skanderborg",
                "kommune": "Skanderborg Kommune",
                "contact_name": "Louise Andersen",
                "contact_email": "la@engdalskolen.dk",
                "contact_phone": "86 52 12 34",
                "contact_role": PersonRole.KOORDINATOR,
            },
            {
                "name": "Skovvangskolen",
                "adresse": "Skovvangen 10, 7400 Herning",
                "kommune": "Herning Kommune",
                "contact_name": "Thomas Rasmussen",
                "contact_email": "tr@skovvangskolen.dk",
                "contact_phone": "97 12 34 56",
                "contact_role": PersonRole.KOORDINATOR,
            },
            {
                "name": "Østervangskolen",
                "adresse": "Østervang 25, 5700 Svendborg",
                "kommune": "Svendborg Kommune",
                "contact_name": "Camilla Olsen",
                "contact_email": "co@ostervangskolen.dk",
                "contact_phone": "62 21 00 00",
                "contact_role": PersonRole.UDSKOLINGSLEDER,
            },
            {
                "name": "Nordvestskolen",
                "adresse": "Nordvestgade 8, 8800 Viborg",
                "kommune": "Viborg Kommune",
                "contact_name": "Henrik Thomsen",
                "contact_email": "ht@nordvestskolen.dk",
                "contact_phone": "86 62 45 00",
                "contact_role": PersonRole.KOORDINATOR,
            },
            {
                "name": "Kildeskovskolen",
                "adresse": "Kildeskovvej 15, 4700 Næstved",
                "kommune": "Næstved Kommune",
                "contact_name": "Marie Kjær",
                "contact_email": "mk@kildeskovskolen.dk",
                "contact_phone": "55 77 15 00",
                "contact_role": PersonRole.KOORDINATOR,
            },
        ]

        schools = []

        # Define school year boundaries for better test data
        # Current year is 2025/26 (Aug 2025 - Jul 2026)
        # Previous year is 2024/25 (Aug 2024 - Jul 2025)
        year_2024_25_start = date(2024, 8, 1)
        year_2025_26_start = date(2025, 8, 1)

        for i, data in enumerate(schools_data):
            # Extract contact info before creating school
            contact_name = data.pop("contact_name")
            contact_email = data.pop("contact_email")
            contact_phone = data.pop("contact_phone")
            contact_role = data.pop("contact_role")

            # Distribute schools across different enrollment periods for testing goals
            if i < 2:
                # Enrolled before 2024/25 (anchoring in both years)
                data["enrolled_at"] = date(2023, 9, 15) + timedelta(days=random.randint(0, 60))
            elif i < 5:
                # Enrolled in 2024/25 (new last year, anchoring this year)
                data["enrolled_at"] = year_2024_25_start + timedelta(days=random.randint(30, 300))
            elif i < 9:
                # Enrolled in 2025/26 (new this year)
                data["enrolled_at"] = year_2025_26_start + timedelta(days=random.randint(30, 150))
            elif i < 11:
                # Not enrolled yet
                data["enrolled_at"] = None
            else:
                # Frameldt (enrolled then opted out)
                data["enrolled_at"] = date(2024, 10, 1)
                data["opted_out_at"] = date(2025, 6, 15)

            school, created = School.objects.get_or_create(name=data["name"], defaults=data)
            if created:
                schools.append(school)
                # Create primary contact person
                Person.objects.create(
                    school=school,
                    name=contact_name,
                    email=contact_email,
                    phone=contact_phone,
                    role=contact_role,
                    is_primary=True,
                )
                # Add a second person for some schools
                if random.random() > 0.5:
                    second_names = ["Jonas Mikkelsen", "Lise Holm", "Frederik Lund", "Maria Krogh"]
                    Person.objects.create(
                        school=school,
                        name=random.choice(second_names),
                        email=f'kontakt@{school.name.lower().replace(" ", "-")}.dk',
                        role=random.choice([PersonRole.SKOLELEDER, PersonRole.UDSKOLINGSLEDER]),
                        is_primary=False,
                    )

        return schools

    def create_courses(self):
        today = date.today()

        # Generate month names for course titles
        months = [
            "Januar",
            "Februar",
            "Marts",
            "April",
            "Maj",
            "Juni",
            "Juli",
            "August",
            "September",
            "Oktober",
            "November",
            "December",
        ]

        def get_month_name(d):
            return months[d.month - 1]

        courses_data = [
            # === 2024/25 school year courses (Aug 2024 - Jul 2025) ===
            {
                "title": "Introduktion til Basal - September 2024",
                "start_date": date(2024, 9, 15),
                "end_date": date(2024, 9, 15),
                "location": "København",
                "capacity": 25,
                "is_published": True,
                "comment": "Grundlæggende introduktion til Basal-metoden",
            },
            {
                "title": "Introduktion til Basal - November 2024",
                "start_date": date(2024, 11, 10),
                "end_date": date(2024, 11, 10),
                "location": "Aarhus",
                "capacity": 20,
                "is_published": True,
                "comment": "Grundlæggende introduktion til Basal-metoden",
            },
            {
                "title": "Basal for skoleledere - Januar 2025",
                "start_date": date(2025, 1, 20),
                "end_date": date(2025, 1, 20),
                "location": "Odense",
                "capacity": 15,
                "is_published": True,
                "comment": "Kursus rettet mod skoleledere og mellemledere",
            },
            {
                "title": "Introduktion til Basal - Marts 2025",
                "start_date": date(2025, 3, 5),
                "end_date": date(2025, 3, 5),
                "location": "Aalborg",
                "capacity": 25,
                "is_published": True,
            },
            {
                "title": "Basal Fortsætter - Maj 2025",
                "start_date": date(2025, 5, 12),
                "end_date": date(2025, 5, 13),
                "location": "Roskilde",
                "capacity": 20,
                "is_published": True,
                "comment": "To-dages fortsætterkursus",
            },
            # === 2025/26 school year courses (Aug 2025 - Jul 2026) ===
            {
                "title": "Introduktion til Basal - September 2025",
                "start_date": date(2025, 9, 18),
                "end_date": date(2025, 9, 18),
                "location": "København",
                "capacity": 30,
                "is_published": True,
                "comment": "Grundlæggende introduktion til Basal-metoden",
            },
            {
                "title": "Introduktion til Basal - November 2025",
                "start_date": date(2025, 11, 6),
                "end_date": date(2025, 11, 6),
                "location": "Vejle",
                "capacity": 25,
                "is_published": True,
            },
            {
                "title": f"Basal opfølgning - {get_month_name(today + timedelta(days=14))} 2026",
                "start_date": today + timedelta(days=14),
                "end_date": today + timedelta(days=14),
                "location": "Aarhus",
                "capacity": 25,
                "is_published": True,
                "comment": "Opfølgningskursus for deltagere der har taget introduktionen",
            },
            {
                "title": f"Introduktion til Basal - {get_month_name(today + timedelta(days=30))} 2026",
                "start_date": today + timedelta(days=30),
                "end_date": today + timedelta(days=30),
                "location": "Odense",
                "capacity": 30,
                "is_published": True,
            },
            {
                "title": f"Basal Fortsætter - {get_month_name(today + timedelta(days=60))} 2026",
                "start_date": today + timedelta(days=60),
                "end_date": today + timedelta(days=61),
                "location": "København",
                "capacity": 15,
                "is_published": True,
                "comment": "To-dages fortsætterkursus",
            },
            # Unpublished course
            {
                "title": "Introduktion til Basal - April 2026",
                "start_date": date(2026, 4, 15),
                "end_date": date(2026, 4, 15),
                "location": "Herning",
                "capacity": 30,
                "is_published": False,
                "comment": "Endnu ikke offentliggjort",
            },
        ]

        courses = []
        for data in courses_data:
            course, created = Course.objects.get_or_create(
                title=data["title"], start_date=data["start_date"], defaults=data
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
            "Anders",
            "Birgitte",
            "Christian",
            "Dorte",
            "Erik",
            "Fie",
            "Gustav",
            "Hanne",
            "Ivan",
            "Julie",
            "Klaus",
            "Lene",
            "Martin",
            "Nanna",
            "Ole",
            "Pia",
            "Rasmus",
            "Sara",
            "Torben",
            "Ulla",
        ]
        last_names = [
            "Jensen",
            "Nielsen",
            "Hansen",
            "Pedersen",
            "Andersen",
            "Christensen",
            "Larsen",
            "Sørensen",
            "Rasmussen",
            "Thomsen",
        ]
        # Titles with is_underviser flag (True for teachers, False for leaders/others)
        titles_with_role = [
            ("Lærer", True),
            ("Lærer", True),
            ("Lærer", True),
            ("Lærer", True),
            ("Indskolingslærer", True),
            ("Mellemtrinslærer", True),
            ("Udskolingslærer", True),
            ("Skoleleder", False),
            ("Viceskoleleder", False),
            ("Afdelingsleder", False),
            ("Pædagog", False),
        ]

        signups = []

        # Track remaining seats per school (all signups count against seats)
        school_remaining_seats = {s.pk: s.total_seats for s in enrolled_schools}

        for course in all_courses:
            # More signups for past courses, fewer for future courses
            today = date.today()
            if course.end_date < today:
                # Past courses: 8-15 signups
                num_signups = random.randint(8, min(15, course.capacity))
            else:
                # Future courses: 3-8 signups
                num_signups = random.randint(3, min(8, course.capacity))

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
                name = f"{first} {last}"
                # Generate email from name and school domain
                email_name = f"{first.lower()}.{last.lower()}"
                # Get domain from primary person's email
                primary_person = school.people.filter(is_primary=True).first()
                if primary_person and primary_person.email and "@" in primary_person.email:
                    school_domain = primary_person.email.split("@")[1]
                else:
                    school_domain = f'{school.name.lower().replace(" ", "-")}.dk'
                email = f"{email_name}@{school_domain}"

                # Select a random title and corresponding is_underviser value
                title, is_underviser = random.choice(titles_with_role)

                try:
                    signup = CourseSignUp.objects.create(
                        school=school,
                        course=course,
                        participant_name=name,
                        participant_email=email,
                        participant_title=title,
                        is_underviser=is_underviser,
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
            return random.choices([AttendanceStatus.PRESENT, AttendanceStatus.ABSENT], weights=[0.85, 0.15])[0]
        else:
            # Future course - unmarked
            return AttendanceStatus.UNMARKED

    def create_contacts(self, schools):
        all_schools = list(School.objects.active())
        if not all_schools:
            return []

        # Create or get staff users for contacts
        esther, _ = User.objects.get_or_create(
            username="esther",
            defaults={
                "first_name": "Esther",
                "last_name": "Chemnitz",
                "email": "esther@basal.dk",
                "is_staff": True,
            },
        )
        esther.set_password("hejhejhej")
        esther.save()

        caroline, _ = User.objects.get_or_create(
            username="caroline",
            defaults={
                "first_name": "Caroline",
                "last_name": "Buskov",
                "email": "caroline@basal.dk",
                "is_staff": True,
            },
        )
        caroline.set_password("hejhejhej")
        caroline.save()

        staff_users = [esther, caroline]

        comments = [
            "Talte med skoleleder om tilmelding til Basal. God interesse.",
            "Sendt information om kommende kurser.",
            "Opfølgning på tidligere kursusdeltagelse. Ønsker flere pladser.",
            "Koordineret praktiske detaljer omkring kursusdeltagelse.",
            "Diskuterede muligheder for fortsætterkursus.",
            "Modtaget feedback fra tidligere kursus. Meget positive tilbagemeldinger.",
            "Aftalt at sende opdateret kursusoversigt til lærerne.",
            "Gennemgået tilmeldingsprocedure med ny kontaktperson.",
            "Bekræftet deltagelse i kommende introduktionskursus.",
            "Drøftet behov for ekstra pladser til næste skoleår.",
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
                    contacted_time = (
                        timezone.now().time().replace(hour=random.randint(8, 17), minute=random.choice([0, 15, 30, 45]))
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
