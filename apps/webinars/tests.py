from datetime import timedelta

import pytest
from django.utils import timezone

from apps.webinars.models import Webinar, WebinarAccessMode


@pytest.mark.django_db
def test_webinar_is_full_returns_false_when_capacity_is_none():
    w = Webinar.objects.create(
        title="Trivsel",
        slug="trivsel",
        start_at=timezone.now() + timedelta(days=7),
        meeting_url="https://example.com/zoom/abc",
        capacity=None,
    )
    assert w.is_full is False


@pytest.mark.django_db
def test_webinar_is_full_true_when_at_capacity():
    w = Webinar.objects.create(
        title="Trivsel",
        slug="trivsel-2",
        start_at=timezone.now() + timedelta(days=7),
        meeting_url="https://example.com/zoom/abc",
        capacity=0,
    )
    assert w.is_full is True


@pytest.mark.django_db
def test_webinar_is_past_true_when_start_at_in_past():
    w = Webinar.objects.create(
        title="Past",
        slug="past",
        start_at=timezone.now() - timedelta(days=1),
        meeting_url="https://example.com/zoom/abc",
    )
    assert w.is_past is True


@pytest.mark.django_db
def test_webinar_end_at_is_start_plus_duration():
    start = timezone.now() + timedelta(days=7)
    w = Webinar.objects.create(
        title="Trivsel",
        slug="trivsel-3",
        start_at=start,
        duration_minutes=90,
        meeting_url="https://example.com/zoom/abc",
    )
    assert w.end_at == start + timedelta(minutes=90)


@pytest.mark.django_db
def test_webinar_default_access_mode_is_public():
    w = Webinar.objects.create(
        title="Trivsel",
        slug="trivsel-4",
        start_at=timezone.now() + timedelta(days=7),
        meeting_url="https://example.com/zoom/abc",
    )
    assert w.access_mode == WebinarAccessMode.PUBLIC
