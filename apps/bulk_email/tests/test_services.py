from django.test import TestCase, override_settings

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
        recipients = resolve_recipients(schools, BulkEmail.KOORDINATOR)
        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0][0], self.school_with_coord)

    def test_skipped_count_correct(self):
        schools = School.objects.filter(pk__in=[self.school_with_coord.pk, self.school_without_coord.pk])
        recipients = resolve_recipients(schools, BulkEmail.KOORDINATOR)
        self.assertEqual(len(recipients), 1)


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
            recipient_type=BulkEmail.KOORDINATOR,
        )

    def test_dev_mode_creates_recipient_with_success(self):
        recipient = send_to_school(self.campaign, self.school, self.person)
        self.assertIsInstance(recipient, BulkEmailRecipient)
        self.assertTrue(recipient.success)
        self.assertIn("DEV MODE", recipient.error_message)

    def test_dev_mode_snapshots_email(self):
        recipient = send_to_school(self.campaign, self.school, self.person)
        self.assertEqual(recipient.email, "person@test.dk")
