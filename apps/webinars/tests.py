from datetime import date, timedelta
from datetime import timedelta as _td

import pytest
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.utils import timezone

from apps.schools.models import Kommune, School
from apps.webinars.forms import GatedWebinarSignupForm, PublicWebinarSignupForm
from apps.webinars.models import Webinar, WebinarAccessMode, WebinarSignUp


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


def _make_webinar(slug="w", access_mode=WebinarAccessMode.PUBLIC):
    return Webinar.objects.create(
        title="W",
        slug=slug,
        start_at=timezone.now() + timedelta(days=7),
        meeting_url="https://example.com/zoom/abc",
        access_mode=access_mode,
    )


@pytest.fixture
def enrolled_school(db):
    kommune = Kommune.objects.create(name="Test Kommune")
    return School.objects.create(
        name="Test Skole",
        adresse="Adresse 1",
        kommune=kommune,
        enrolled_at=date.today() - _td(days=30),
    )


@pytest.mark.django_db
def test_webinar_signup_unique_email_per_webinar(enrolled_school):
    w = _make_webinar()
    WebinarSignUp.objects.create(webinar=w, participant_name="A", participant_email="dup@example.com")
    with pytest.raises(IntegrityError):
        WebinarSignUp.objects.create(webinar=w, participant_name="B", participant_email="dup@example.com")


@pytest.mark.django_db
def test_webinar_signup_same_email_allowed_across_different_webinars():
    w1 = _make_webinar(slug="a")
    w2 = _make_webinar(slug="b")
    WebinarSignUp.objects.create(webinar=w1, participant_name="A", participant_email="x@y.dk")
    # Should not raise
    WebinarSignUp.objects.create(webinar=w2, participant_name="A", participant_email="x@y.dk")


@pytest.mark.django_db
def test_webinar_signup_clean_requires_school_for_gated_webinar():
    w = _make_webinar(slug="g", access_mode=WebinarAccessMode.SCHOOL_GATED)
    s = WebinarSignUp(webinar=w, participant_name="A", participant_email="x@y.dk", school=None)
    with pytest.raises(ValidationError):
        s.full_clean()


@pytest.mark.django_db
def test_webinar_signup_clean_rejects_school_for_public_webinar(enrolled_school):
    w = _make_webinar(slug="p2")
    s = WebinarSignUp(webinar=w, school=enrolled_school, participant_name="A", participant_email="x@y.dk")
    with pytest.raises(ValidationError):
        s.full_clean()


@pytest.mark.django_db
def test_webinar_signup_clears_bounce_on_email_change():
    w = _make_webinar(slug="bn")
    s = WebinarSignUp.objects.create(webinar=w, participant_name="A", participant_email="old@example.com")
    s.email_bounced_at = timezone.now()
    s.save()
    s.participant_email = "new@example.com"
    s.save()
    s.refresh_from_db()
    assert s.email_bounced_at is None


@pytest.mark.django_db
def test_public_form_requires_name_and_email():
    form = PublicWebinarSignupForm(data={})
    assert not form.is_valid()
    assert "name" in form.errors
    assert "email" in form.errors


@pytest.mark.django_db
def test_public_form_accepts_minimal_valid_data():
    form = PublicWebinarSignupForm(data={"name": "Anna", "email": "a@b.dk"})
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_public_form_includes_organization_field():
    form = PublicWebinarSignupForm(data={"name": "A", "email": "a@b.dk", "organization": "Acme"})
    assert form.is_valid(), form.errors
    assert form.cleaned_data["organization"] == "Acme"


@pytest.mark.django_db
def test_gated_form_requires_name_and_email():
    form = GatedWebinarSignupForm(data={})
    assert not form.is_valid()
    assert "name" in form.errors
    assert "email" in form.errors


@pytest.mark.django_db
def test_gated_form_does_not_have_organization_field():
    form = GatedWebinarSignupForm(data={"name": "A", "email": "a@b.dk"})
    assert "organization" not in form.fields
