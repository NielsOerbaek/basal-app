from datetime import date, timedelta
from datetime import timedelta as _td

import pytest
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import Client
from django.utils import timezone

from apps.emails.services import (
    get_webinar_signup_context,
    send_webinar_signup_confirmation,
    send_webinar_signup_notification,
)
from apps.schools.models import Kommune, School
from apps.signups.auth import SCHOOL_SESSION_KEY
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


@pytest.mark.django_db
def test_webinar_signup_context_includes_meeting_url():
    w = _make_webinar(slug="ctx")
    s = WebinarSignUp.objects.create(webinar=w, participant_name="Anna", participant_email="a@b.dk")
    ctx = get_webinar_signup_context(s)
    assert ctx["meeting_url"] == w.meeting_url
    assert ctx["webinar_title"] == w.title
    assert ctx["participant_name"] == "Anna"


@pytest.mark.django_db
def test_send_webinar_signup_confirmation_returns_true_in_dev_mode():
    # conftest sets RESEND_API_KEY = None — the function should log and return True
    w = _make_webinar(slug="cf")
    s = WebinarSignUp.objects.create(webinar=w, participant_name="Anna", participant_email="a@b.dk")
    assert send_webinar_signup_confirmation(s) is True


@pytest.mark.django_db
def test_send_webinar_signup_notification_returns_true_in_dev_mode():
    w = _make_webinar(slug="nt")
    s = WebinarSignUp.objects.create(
        webinar=w, participant_name="Anna", participant_email="a@b.dk", organization="Acme"
    )
    assert send_webinar_signup_notification(w, s) is True


@pytest.mark.django_db
def test_unpublished_webinar_returns_404():
    w = _make_webinar(slug="unpub")
    client = Client()
    resp = client.get(f"/webinar/{w.slug}/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_published_public_webinar_renders_form():
    w = _make_webinar(slug="open")
    w.is_published = True
    w.save()
    client = Client()
    resp = client.get(f"/webinar/{w.slug}/")
    assert resp.status_code == 200
    assert b"Tilmeld" in resp.content


@pytest.mark.django_db
def test_past_webinar_replaces_form_with_message():
    w = Webinar.objects.create(
        title="Past",
        slug="ended",
        start_at=timezone.now() - timedelta(days=1),
        meeting_url="https://example.com/zoom/abc",
        is_published=True,
    )
    client = Client()
    resp = client.get(f"/webinar/{w.slug}/")
    assert resp.status_code == 200
    assert b"har allerede fundet sted" in resp.content


@pytest.mark.django_db
def test_full_webinar_replaces_form_with_message():
    w = Webinar.objects.create(
        title="Full",
        slug="full",
        start_at=timezone.now() + timedelta(days=7),
        meeting_url="https://example.com/zoom/abc",
        capacity=1,
        is_published=True,
    )
    WebinarSignUp.objects.create(webinar=w, participant_name="A", participant_email="a@b.dk")
    client = Client()
    resp = client.get(f"/webinar/{w.slug}/")
    assert b"Fuldt" in resp.content


@pytest.mark.django_db
def test_public_signup_creates_record_and_redirects():
    w = _make_webinar(slug="post")
    w.is_published = True
    w.save()
    client = Client()
    resp = client.post(
        f"/webinar/{w.slug}/",
        {"name": "Anna", "email": "a@b.dk", "organization": "Acme"},
    )
    assert resp.status_code == 302
    assert resp.url == f"/webinar/{w.slug}/tak/"
    s = WebinarSignUp.objects.get(webinar=w)
    assert s.participant_name == "Anna"
    assert s.school is None
    assert s.organization == "Acme"


@pytest.mark.django_db
def test_public_signup_rejects_duplicate_email():
    w = _make_webinar(slug="dup")
    w.is_published = True
    w.save()
    WebinarSignUp.objects.create(webinar=w, participant_name="A", participant_email="dup@x.dk")
    client = Client()
    resp = client.post(f"/webinar/{w.slug}/", {"name": "B", "email": "dup@x.dk"})
    assert resp.status_code == 200
    assert b"allerede tilmeldt" in resp.content


@pytest.mark.django_db
def test_success_page_renders():
    w = _make_webinar(slug="suc")
    w.is_published = True
    w.save()
    client = Client()
    resp = client.get(f"/webinar/{w.slug}/tak/")
    assert resp.status_code == 200


@pytest.fixture
def gated_webinar():
    return Webinar.objects.create(
        title="Gated",
        slug="gated",
        start_at=timezone.now() + timedelta(days=7),
        meeting_url="https://example.com/zoom/abc",
        access_mode=WebinarAccessMode.SCHOOL_GATED,
        is_published=True,
    )


@pytest.mark.django_db
def test_gated_webinar_unauthenticated_shows_password_form(gated_webinar):
    client = Client()
    resp = client.get(f"/webinar/{gated_webinar.slug}/")
    assert resp.status_code == 200
    assert b"Indtast skolekode" in resp.content


@pytest.mark.django_db
def test_gated_webinar_token_in_url_authenticates(gated_webinar, enrolled_school):
    enrolled_school.generate_credentials()
    client = Client()
    resp = client.get(f"/webinar/{gated_webinar.slug}/?token={enrolled_school.signup_token}")
    assert resp.status_code == 200
    assert b"Indtast skolekode" not in resp.content


@pytest.mark.django_db
def test_gated_webinar_session_school_authenticates(gated_webinar, enrolled_school):
    client = Client()
    session = client.session
    session[SCHOOL_SESSION_KEY] = enrolled_school.pk
    session.save()
    resp = client.get(f"/webinar/{gated_webinar.slug}/")
    assert resp.status_code == 200
    assert b"Indtast skolekode" not in resp.content


@pytest.mark.django_db
def test_gated_webinar_signup_creates_record_with_school(gated_webinar, enrolled_school):
    client = Client()
    session = client.session
    session[SCHOOL_SESSION_KEY] = enrolled_school.pk
    session.save()
    resp = client.post(
        f"/webinar/{gated_webinar.slug}/",
        {"name": "Anna", "email": "a@b.dk"},
    )
    assert resp.status_code == 302
    s = WebinarSignUp.objects.get(webinar=gated_webinar)
    assert s.school_id == enrolled_school.pk
    assert s.organization == ""


@pytest.mark.django_db
def test_gated_webinar_does_not_require_ean_or_oekonomisk_ansvarlig(gated_webinar, enrolled_school):
    """Regression guard: webinars are free, so EAN/økonomisk gating from
    course signups must NOT be applied here.
    """
    enrolled_school.ean_nummer = ""
    enrolled_school.kommunen_betaler = False
    enrolled_school.save()
    # No økonomisk ansvarlig is created either.
    client = Client()
    session = client.session
    session[SCHOOL_SESSION_KEY] = enrolled_school.pk
    session.save()
    resp = client.post(f"/webinar/{gated_webinar.slug}/", {"name": "Anna", "email": "a@b.dk"})
    assert resp.status_code == 302
    assert WebinarSignUp.objects.filter(webinar=gated_webinar).count() == 1


@pytest.mark.django_db
def test_public_webinar_with_session_school_treats_as_public(enrolled_school):
    public = Webinar.objects.create(
        title="Public",
        slug="pub-with-school",
        start_at=timezone.now() + timedelta(days=7),
        meeting_url="https://example.com/zoom/abc",
        is_published=True,
    )
    client = Client()
    session = client.session
    session[SCHOOL_SESSION_KEY] = enrolled_school.pk
    session.save()
    resp = client.post(
        f"/webinar/{public.slug}/",
        {"name": "Anna", "email": "a@b.dk", "organization": "Self"},
    )
    assert resp.status_code == 302
    s = WebinarSignUp.objects.get(webinar=public)
    assert s.school is None
    assert s.organization == "Self"
