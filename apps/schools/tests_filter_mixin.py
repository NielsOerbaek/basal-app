from django.test import RequestFactory, TestCase

from apps.schools.mixins import SchoolFilterMixin
from apps.schools.models import School, SchoolYear


class DummyView(SchoolFilterMixin):
    def __init__(self, request):
        self.request = request


class SchoolFilterMixinContextTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        SchoolYear.objects.get_or_create(
            name="2024/25",
            defaults={
                "start_date": "2024-08-01",
                "end_date": "2025-07-31",
            },
        )
        School.objects.create(
            name="Testskole",
            kommune="Aarhus",
            signup_token="tok",
            signup_password="pw",
        )

    def test_get_filter_context_has_required_keys(self):
        request = self.factory.get("/masseudsendelse/ny/")
        request.GET = request.GET.copy()
        view = DummyView(request)
        ctx = view.get_filter_context()
        for key in (
            "kommuner",
            "school_years",
            "filter_summary",
            "has_active_filters",
            "selected_year",
            "selected_year_dates",
        ):
            self.assertIn(key, ctx)

    def test_has_active_filters_false_when_no_params(self):
        request = self.factory.get("/masseudsendelse/ny/")
        view = DummyView(request)
        ctx = view.get_filter_context()
        self.assertFalse(ctx["has_active_filters"])

    def test_has_active_filters_true_when_search_set(self):
        request = self.factory.get("/masseudsendelse/ny/?search=foo")
        view = DummyView(request)
        ctx = view.get_filter_context()
        self.assertTrue(ctx["has_active_filters"])

    def test_institutionstype_filter(self):
        from apps.schools.models import InstitutionstypeChoice

        School.objects.create(
            name="Friskolen",
            kommune="Aarhus",
            institutionstype=InstitutionstypeChoice.FRISKOLE,
            signup_token="t1",
            signup_password="p1",
        )
        School.objects.create(
            name="Efterskolen",
            kommune="Aarhus",
            institutionstype=InstitutionstypeChoice.EFTERSKOLE,
            signup_token="t2",
            signup_password="p2",
        )
        request = self.factory.get("/?institutionstype=friskole")
        view = DummyView(request)
        names = sorted(s.name for s in view.get_school_filter_queryset())
        self.assertEqual(names, ["Friskolen"])

    def test_institutionstype_filter_multi_select(self):
        from apps.schools.models import InstitutionstypeChoice

        School.objects.create(
            name="Friskolen2",
            kommune="Aarhus",
            institutionstype=InstitutionstypeChoice.FRISKOLE,
            signup_token="m1",
            signup_password="m1",
        )
        School.objects.create(
            name="Efterskolen2",
            kommune="Aarhus",
            institutionstype=InstitutionstypeChoice.EFTERSKOLE,
            signup_token="m2",
            signup_password="m2",
        )
        # Both selected
        request = self.factory.get("/?institutionstype=friskole&institutionstype=efterskole")
        view = DummyView(request)
        names = {s.name for s in view.get_school_filter_queryset()}
        self.assertIn("Friskolen2", names)
        self.assertIn("Efterskolen2", names)
        self.assertNotIn("Testskole", names)  # folkeskole not selected

    def test_institutionstype_filter_kombineret_matches_both(self):
        from apps.schools.models import InstitutionstypeChoice

        School.objects.create(
            name="Kombineret",
            kommune="Aarhus",
            institutionstype=InstitutionstypeChoice.FRISKOLE_EFTERSKOLE,
            signup_token="t3",
            signup_password="p3",
        )
        for filter_val in ("friskole", "efterskole"):
            request = self.factory.get(f"/?institutionstype={filter_val}")
            view = DummyView(request)
            names = {s.name for s in view.get_school_filter_queryset()}
            self.assertIn("Kombineret", names, f"filter={filter_val} should include kombineret")

    def test_institutionstype_in_filter_summary(self):
        request = self.factory.get("/?institutionstype=efterskole")
        view = DummyView(request)
        ctx = view.get_filter_context()
        self.assertIn("Efterskole", ctx["filter_summary"])

    def test_selected_year_from_request(self):
        request = self.factory.get("/masseudsendelse/ny/?year=2024/25")
        view = DummyView(request)
        ctx = view.get_filter_context()
        self.assertEqual(ctx["selected_year"], "2024/25")

    def test_selected_year_dates_populated_when_year_set(self):
        request = self.factory.get("/masseudsendelse/ny/?year=2024/25")
        view = DummyView(request)
        ctx = view.get_filter_context()
        self.assertIsNotNone(ctx["selected_year_dates"])

    def test_selected_year_dates_none_when_no_year(self):
        request = self.factory.get("/masseudsendelse/ny/")
        view = DummyView(request)
        ctx = view.get_filter_context()
        self.assertIsNone(ctx["selected_year_dates"])

    def test_school_years_list(self):
        request = self.factory.get("/masseudsendelse/ny/")
        view = DummyView(request)
        ctx = view.get_filter_context()
        self.assertIn("2024/25", list(ctx["school_years"]))


class SchoolFilterMixinQuerysetTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        School.objects.create(
            name="Aarhus Skole",
            kommune="Aarhus",
            signup_token="tok1",
            signup_password="pw1",
        )
        School.objects.create(
            name="Odense Skole",
            kommune="Odense",
            signup_token="tok2",
            signup_password="pw2",
        )

    def test_no_filters_returns_active_schools(self):
        request = self.factory.get("/")
        view = DummyView(request)
        qs = view.get_school_filter_queryset()
        self.assertEqual(len(list(qs)), 2)

    def test_search_filters_by_name(self):
        request = self.factory.get("/?search=Aarhus")
        view = DummyView(request)
        qs = list(view.get_school_filter_queryset())
        self.assertEqual(len(qs), 1)
        self.assertEqual(qs[0].name, "Aarhus Skole")

    def test_kommune_filter(self):
        request = self.factory.get("/?kommune=Odense")
        view = DummyView(request)
        qs = list(view.get_school_filter_queryset())
        self.assertEqual(len(qs), 1)
        self.assertEqual(qs[0].name, "Odense Skole")
