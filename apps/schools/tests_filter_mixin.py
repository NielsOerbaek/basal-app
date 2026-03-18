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
