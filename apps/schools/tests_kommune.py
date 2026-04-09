"""Tests for the Kommune model and kommune-shared billing logic."""

from django.test import RequestFactory, TestCase

from apps.schools.forms import SchoolForm
from apps.schools.kommuner import KOMMUNE_NAMES
from apps.schools.models import Kommune, School, apply_billing_to_school


class KommuneModelTest(TestCase):
    def test_get_for_returns_none_when_missing(self):
        self.assertIsNone(Kommune.get_for("Aarhus"))

    def test_get_or_create_for_creates_row(self):
        k = Kommune.get_or_create_for("Aarhus")
        self.assertEqual(k.name, "Aarhus")
        self.assertEqual(Kommune.objects.count(), 1)
        # Idempotent
        k2 = Kommune.get_or_create_for("Aarhus")
        self.assertEqual(k.pk, k2.pk)

    def test_email_change_clears_bounce(self):
        from django.utils import timezone

        k = Kommune.objects.create(
            name="Aarhus",
            fakturering_kontakt_email="old@example.com",
            fakturering_email_bounced_at=timezone.now(),
        )
        k.fakturering_kontakt_email = "new@example.com"
        k.save()
        k.refresh_from_db()
        self.assertIsNone(k.fakturering_email_bounced_at)


class ApplyBillingHelperTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="Test School", kommune="Aarhus Kommune", kommunen_betaler=True)

    def test_writes_to_kommune_when_kommunen_betaler(self):
        data = {
            "fakturering_adresse": "Hovedgaden 1",
            "fakturering_postnummer": "8000",
            "fakturering_by": "Aarhus",
            "fakturering_ean_nummer": "12345678",
            "fakturering_kontakt_navn": "Anne",
            "fakturering_kontakt_email": "anne@aarhus.dk",
        }
        result = apply_billing_to_school(self.school, data)
        self.school.save()

        self.assertIsNotNone(result)
        self.assertEqual(result.name, "Aarhus Kommune")
        self.assertEqual(result.fakturering_ean_nummer, "12345678")
        # School fields are cleared
        self.school.refresh_from_db()
        self.assertEqual(self.school.fakturering_adresse, "")
        self.assertEqual(self.school.fakturering_ean_nummer, "")

    def test_writes_to_school_when_not_kommunen_betaler(self):
        self.school.kommunen_betaler = False
        data = {
            "fakturering_adresse": "Privatvej 2",
            "fakturering_postnummer": "8000",
            "fakturering_by": "Aarhus",
            "fakturering_ean_nummer": "99999999",
            "fakturering_kontakt_navn": "Bob",
            "fakturering_kontakt_email": "bob@example.com",
        }
        result = apply_billing_to_school(self.school, data)
        self.school.save()

        self.assertIsNone(result)
        self.assertEqual(Kommune.objects.count(), 0)
        self.school.refresh_from_db()
        self.assertEqual(self.school.fakturering_ean_nummer, "99999999")


class SchoolFormKommuneSaveTest(TestCase):
    def test_save_routes_to_kommune(self):
        school = School.objects.create(name="Skole A", kommune="Aarhus Kommune")
        post_data = {
            "name": "Skole A",
            "institutionstype": "folkeskole",
            "adresse": "",
            "postnummer": "",
            "by": "",
            "kommune": "Aarhus Kommune",
            "ean_nummer": "",
            "kommunen_betaler": "on",
            "fakturering_adresse": "Hovedgaden 1",
            "fakturering_postnummer": "8000",
            "fakturering_by": "Aarhus",
            "fakturering_ean_nummer": "12345678",
            "fakturering_kontakt_navn": "Anne",
            "fakturering_kontakt_email": "anne@aarhus.dk",
        }
        form = SchoolForm(post_data, instance=school)
        self.assertTrue(form.is_valid(), msg=form.errors)
        form.save()

        kommune = Kommune.get_for("Aarhus Kommune")
        self.assertIsNotNone(kommune)
        self.assertEqual(kommune.fakturering_ean_nummer, "12345678")
        school.refresh_from_db()
        self.assertEqual(school.fakturering_ean_nummer, "")
        self.assertTrue(school.kommunen_betaler)

    def test_form_initial_loads_from_kommune(self):
        Kommune.objects.create(
            name="Aarhus Kommune",
            fakturering_ean_nummer="55555555",
            fakturering_kontakt_email="shared@aarhus.dk",
        )
        school = School.objects.create(name="Skole B", kommune="Aarhus Kommune", kommunen_betaler=True)
        form = SchoolForm(instance=school)
        self.assertEqual(form.initial["fakturering_ean_nummer"], "55555555")
        self.assertEqual(form.initial["fakturering_kontakt_email"], "shared@aarhus.dk")


class SchoolDetailBillingSourceTest(TestCase):
    def test_kommune_billing_used_in_context(self):
        from apps.schools.views import SchoolDetailView

        Kommune.objects.create(name="Aarhus Kommune", fakturering_ean_nummer="55555555")
        school = School.objects.create(name="Skole C", kommune="Aarhus Kommune", kommunen_betaler=True)
        view = SchoolDetailView()
        view.object = school
        view.kwargs = {"pk": school.pk}
        view.request = RequestFactory().get("/")
        ctx = view.get_context_data()
        self.assertTrue(ctx["billing_from_kommune"])
        self.assertEqual(ctx["billing_source"].fakturering_ean_nummer, "55555555")

    def test_school_billing_used_when_no_kommune_row(self):
        from apps.schools.views import SchoolDetailView

        school = School.objects.create(
            name="Skole D",
            kommune="Aarhus Kommune",
            kommunen_betaler=True,
            fakturering_ean_nummer="11111111",
        )
        view = SchoolDetailView()
        view.object = school
        view.kwargs = {"pk": school.pk}
        view.request = RequestFactory().get("/")
        ctx = view.get_context_data()
        self.assertFalse(ctx["billing_from_kommune"])
        self.assertIsNone(ctx["billing_source"])


class BackfillCanonicalPickTest(TestCase):
    def test_picks_longest_when_all_unique(self):
        # Inline import to avoid migrations module path issues
        import importlib

        mod = importlib.import_module("apps.schools.migrations.0037_backfill_kommune_billing")
        pick = mod._pick_canonical
        self.assertEqual(pick(["abc", "abcd", "ab"]), "abcd")

    def test_majority_wins_over_longer(self):
        import importlib

        mod = importlib.import_module("apps.schools.migrations.0037_backfill_kommune_billing")
        pick = mod._pick_canonical
        self.assertEqual(pick(["abc", "abc", "abcdef"]), "abc")

    def test_ignores_blank(self):
        import importlib

        mod = importlib.import_module("apps.schools.migrations.0037_backfill_kommune_billing")
        pick = mod._pick_canonical
        self.assertEqual(pick(["", "  ", "real"]), "real")


class SeedKommunerTest(TestCase):
    def test_all_98_kommuner_present(self):
        names_in_db = set(Kommune.objects.values_list("name", flat=True))
        for name in KOMMUNE_NAMES:
            self.assertIn(name, names_in_db, f"{name} missing from Kommune table")
        self.assertGreaterEqual(Kommune.objects.count(), 98)
