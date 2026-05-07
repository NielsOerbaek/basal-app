from django.test import TestCase, override_settings
from django.utils import timezone

from apps.bulk_email.models import BulkEmail, BulkEmailRecipient
from apps.bulk_email.services import (
    build_template_context,
    find_missing_variables,
    resolve_recipients,
    send_to_school,
)
from apps.schools.models import Person, School


class BuildTemplateContextTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Testskole A/S",
            adresse="Testvej 1",
            postnummer="8000",
            by="Aarhus",
            kommune="Aarhus",
            ean_nummer="1234567890123",
            enrolled_at="2024-08-01",
            active_from="2024-08-01",
            signup_token="abc123",
            signup_password="hemlig",
        )
        self.person = Person.objects.create(
            school=self.school,
            name="Kontakt Person",
            email="kontakt@testskole.dk",
            phone="11223344",
        )

    def test_school_name_mapped(self):
        ctx = build_template_context(self.school, self.person)
        self.assertEqual(ctx["skole_navn"], "Testskole A/S")

    def test_person_fields_mapped(self):
        ctx = build_template_context(self.school, self.person)
        self.assertEqual(ctx["kontakt_navn"], "Kontakt Person")
        self.assertEqual(ctx["kontakt_email"], "kontakt@testskole.dk")
        self.assertEqual(ctx["kontakt_telefon"], "11223344")

    def test_tilmeldings_link_contains_token(self):
        ctx = build_template_context(self.school, self.person)
        self.assertIn("abc123", ctx["tilmeldings_link"])

    def test_adgangskode_set(self):
        ctx = build_template_context(self.school, self.person)
        self.assertEqual(ctx["tilmeldings_adgangskode"], "hemlig")


class FindMissingVariablesTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Skole",
            signup_token="tok",
            signup_password="pw",
        )
        self.person = Person.objects.create(
            school=self.school,
            name="Person",
            email="p@s.dk",
        )

    def test_no_warnings_when_all_present(self):
        template_str = "Kære {{ kontakt_navn }}, {{ skole_navn }}"
        warnings = find_missing_variables(template_str, [(self.school, self.person)])
        self.assertEqual(warnings, [])

    def test_warning_when_ean_missing(self):
        # school has no ean_nummer
        template_str = "EAN: {{ ean_nummer }}"
        warnings = find_missing_variables(template_str, [(self.school, self.person)])
        self.assertEqual(len(warnings), 1)
        self.assertIn("ean_nummer", warnings[0]["variable"])
        self.assertIn("Skole", warnings[0]["schools"])


class ResolveRecipientsTest(TestCase):
    def setUp(self):
        self.school_with_coord = School.objects.create(name="Med Koordinator", signup_token="t1", signup_password="p1")
        Person.objects.create(
            school=self.school_with_coord,
            name="Koordinator",
            email="k@test.dk",
            is_koordinator=True,
        )
        self.school_without_coord = School.objects.create(
            name="Uden Koordinator", signup_token="t2", signup_password="p2"
        )

    def test_returns_only_schools_with_matching_contact(self):
        schools = School.objects.filter(pk__in=[self.school_with_coord.pk, self.school_without_coord.pk])
        triples = resolve_recipients(schools, [BulkEmail.KOORDINATOR])
        self.assertEqual(len(triples), 1)
        self.assertEqual(triples[0][0], self.school_with_coord)
        self.assertEqual(triples[0][2], ["Koordinator"])

    def test_skipped_count_correct(self):
        schools = School.objects.filter(pk__in=[self.school_with_coord.pk, self.school_without_coord.pk])
        triples = resolve_recipients(schools, [BulkEmail.KOORDINATOR])
        self.assertEqual(len(triples), 1)


class ResolveRecipientsMultiTypeTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="Multi", signup_token="mt", signup_password="mp")
        self.koord_only = Person.objects.create(
            school=self.school, name="A Koord", email="a@test.dk", is_koordinator=True
        )
        self.oek_only = Person.objects.create(
            school=self.school, name="B Oek", email="b@test.dk", is_oekonomisk_ansvarlig=True
        )
        self.both = Person.objects.create(
            school=self.school,
            name="C Begge",
            email="c@test.dk",
            is_koordinator=True,
            is_oekonomisk_ansvarlig=True,
        )
        self.plain = Person.objects.create(school=self.school, name="D Almen", email="d@test.dk")

    def test_dedupes_person_matching_multiple_types_with_combined_roles(self):
        triples = resolve_recipients(
            School.objects.filter(pk=self.school.pk),
            [BulkEmail.KOORDINATOR, BulkEmail.OEKONOMISK_ANSVARLIG],
        )
        emails_to_roles = {t[1].email: t[2] for t in triples}
        self.assertEqual(set(emails_to_roles.keys()), {"a@test.dk", "b@test.dk", "c@test.dk"})
        self.assertEqual(emails_to_roles["c@test.dk"], ["Koordinator", "Økonomiansvarlig"])

    def test_alle_kontakter_combined_with_koordinator_tags_both(self):
        triples = resolve_recipients(
            School.objects.filter(pk=self.school.pk),
            [BulkEmail.KOORDINATOR, BulkEmail.ALLE_KONTAKTER],
        )
        emails_to_roles = {t[1].email: t[2] for t in triples}
        self.assertEqual(len(triples), 4)
        self.assertEqual(emails_to_roles["a@test.dk"], ["Koordinator", "Alle kontakter"])
        self.assertEqual(emails_to_roles["d@test.dk"], ["Alle kontakter"])

    def test_empty_types_returns_empty(self):
        self.assertEqual(resolve_recipients(School.objects.filter(pk=self.school.pk), []), [])


class ResolveRecipientsUndervisereKursusTest(TestCase):
    def setUp(self):
        from datetime import date

        from apps.courses.models import Course, CourseSignUp

        self.school_a = School.objects.create(name="Skole A", signup_token="ta", signup_password="pa")
        self.school_b = School.objects.create(name="Skole B", signup_token="tb", signup_password="pb")
        self.school_silent = School.objects.create(
            name="Skole Tavs",
            signup_token="tc",
            signup_password="pc",
            do_not_contact_at=timezone.now(),
        )
        self.course = Course.objects.create(start_date=date.today(), end_date=date.today())

        # School A: one underviser with email, one without email, one non-underviser
        CourseSignUp.objects.create(
            school=self.school_a,
            course=self.course,
            participant_name="Anna Underviser",
            participant_email="anna@a.dk",
            is_underviser=True,
        )
        CourseSignUp.objects.create(
            school=self.school_a,
            course=self.course,
            participant_name="Bo Uden Email",
            participant_email="",
            is_underviser=True,
        )
        CourseSignUp.objects.create(
            school=self.school_a,
            course=self.course,
            participant_name="Carl Leder",
            participant_email="carl@a.dk",
            is_underviser=False,
        )
        # School B: duplicate emails across two courses for same school
        CourseSignUp.objects.create(
            school=self.school_b,
            course=self.course,
            participant_name="Dina",
            participant_email="dina@b.dk",
            is_underviser=True,
        )
        CourseSignUp.objects.create(
            school=self.school_b,
            course=self.course,
            participant_name="Dina (again)",
            participant_email="DINA@b.dk",
            is_underviser=True,
        )
        # Silent school: should be skipped despite eligible signup
        CourseSignUp.objects.create(
            school=self.school_silent,
            course=self.course,
            participant_name="Erik",
            participant_email="erik@c.dk",
            is_underviser=True,
        )

    def test_only_includes_undervisere_with_email(self):
        schools = School.objects.filter(pk__in=[self.school_a.pk])
        triples = resolve_recipients(schools, [BulkEmail.UNDERVISERE_KURSUS])
        emails = [p.email for _, p, _ in triples]
        self.assertEqual(emails, ["anna@a.dk"])
        self.assertEqual(triples[0][2], ["Underviser"])

    def test_dedupes_by_email_per_school(self):
        schools = School.objects.filter(pk__in=[self.school_b.pk])
        triples = resolve_recipients(schools, [BulkEmail.UNDERVISERE_KURSUS])
        self.assertEqual(len(triples), 1)
        self.assertEqual(triples[0][1].email, "dina@b.dk")

    def test_skips_do_not_contact_schools(self):
        schools = School.objects.filter(pk__in=[self.school_silent.pk])
        triples = resolve_recipients(schools, [BulkEmail.UNDERVISERE_KURSUS])
        self.assertEqual(triples, [])

    def test_pseudo_person_is_unsaved(self):
        schools = School.objects.filter(pk__in=[self.school_a.pk])
        triples = resolve_recipients(schools, [BulkEmail.UNDERVISERE_KURSUS])
        _, person, _ = triples[0]
        self.assertIsNone(person.pk)
        self.assertEqual(person.name, "Anna Underviser")
        self.assertEqual(person.email, "anna@a.dk")

    def test_underviser_with_existing_person_email_combines_roles(self):
        # Add a koordinator on school_a whose email matches the underviser
        Person.objects.create(
            school=self.school_a,
            name="Anna Underviser",
            email="anna@a.dk",
            is_koordinator=True,
        )
        triples = resolve_recipients(
            School.objects.filter(pk=self.school_a.pk),
            [BulkEmail.KOORDINATOR, BulkEmail.UNDERVISERE_KURSUS],
        )
        self.assertEqual(len(triples), 1)
        self.assertEqual(triples[0][2], ["Koordinator", "Underviser"])


@override_settings(RESEND_API_KEY=None)
class SendToSchoolTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Skole",
            signup_token="tok",
            signup_password="pw",
        )
        self.person = Person.objects.create(
            school=self.school,
            name="Person",
            email="person@test.dk",
            is_koordinator=True,
        )
        self.campaign = BulkEmail.objects.create(
            subject="Test {{ skole_navn }}",
            body_html="<p>Hej {{ kontakt_navn }}</p>",
            recipient_types=[BulkEmail.KOORDINATOR],
        )

    def test_dev_mode_creates_recipient_with_success(self):
        recipient = send_to_school(self.campaign, self.school, self.person)
        self.assertIsInstance(recipient, BulkEmailRecipient)
        self.assertTrue(recipient.success)
        self.assertIn("DEV MODE", recipient.error_message)

    def test_dev_mode_snapshots_email(self):
        recipient = send_to_school(self.campaign, self.school, self.person)
        self.assertEqual(recipient.email, "person@test.dk")

    def test_unsaved_person_persists_recipient_with_null_person_fk(self):
        pseudo = Person(name="Kursus Underviser", email="u@test.dk", phone="")
        recipient = send_to_school(self.campaign, self.school, pseudo)
        self.assertTrue(recipient.success)
        self.assertEqual(recipient.email, "u@test.dk")
        self.assertIsNone(recipient.person_id)
