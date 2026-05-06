from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.db.utils import IntegrityError
from django.test import Client
from django.utils import timezone

from apps.emails.services import (
    get_webinar_signup_context,
    send_webinar_signup_confirmation,
    send_webinar_signup_notification,
)
from apps.schools.models import Kommune
from apps.webinars.forms import WebinarSignupForm
from apps.webinars.models import Webinar, WebinarSignUp


def _make_webinar(slug="w", **kwargs):
    defaults = {
        "title": "W",
        "slug": slug,
        "start_at": timezone.now() + timedelta(days=7),
        "meeting_url": "https://example.com/zoom/abc",
    }
    defaults.update(kwargs)
    return Webinar.objects.create(**defaults)


@pytest.fixture
def kommune(db):
    return Kommune.objects.create(name="Aarhus")


# ---------------------------------------------------------------------------
# Webinar model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_webinar_is_full_returns_false_when_capacity_is_none():
    w = _make_webinar(slug="trivsel", capacity=None)
    assert w.is_full is False


@pytest.mark.django_db
def test_webinar_is_full_true_when_at_capacity():
    w = _make_webinar(slug="trivsel-2", capacity=0)
    assert w.is_full is True


@pytest.mark.django_db
def test_webinar_is_past_true_when_start_at_in_past():
    w = _make_webinar(slug="past", start_at=timezone.now() - timedelta(days=1))
    assert w.is_past is True


@pytest.mark.django_db
def test_webinar_end_at_is_start_plus_duration():
    start = timezone.now() + timedelta(days=7)
    w = _make_webinar(slug="trivsel-3", start_at=start, duration_minutes=90)
    assert w.end_at == start + timedelta(minutes=90)


@pytest.mark.django_db
def test_webinar_get_absolute_url_uses_slug():
    w = _make_webinar(slug="abs-url")
    assert w.get_absolute_url() == "/webinar/abs-url/"


@pytest.mark.django_db
def test_webinar_display_time_combines_date_start_end_and_duration():
    from datetime import datetime

    from django.utils.timezone import make_aware

    start = make_aware(datetime(2026, 10, 12, 18, 0))
    w = _make_webinar(slug="dt", start_at=start, duration_minutes=90)
    assert w.display_time == "12. oktober 2026 18:00 - 19:30 (90 minutter)"


@pytest.mark.django_db
def test_meeting_url_is_optional():
    """meeting_url is now blank=True so admins can publish a webinar
    before they have the Zoom link."""
    w = _make_webinar(slug="no-link", meeting_url="")
    w.full_clean()  # must not raise


# ---------------------------------------------------------------------------
# WebinarSignUp model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_webinar_signup_unique_email_per_webinar(kommune):
    w = _make_webinar()
    WebinarSignUp.objects.create(
        webinar=w, kommune=kommune, school_name="A", participant_name="A", participant_email="dup@example.com"
    )
    with pytest.raises(IntegrityError):
        WebinarSignUp.objects.create(
            webinar=w, kommune=kommune, school_name="A", participant_name="B", participant_email="dup@example.com"
        )


@pytest.mark.django_db
def test_webinar_signup_same_email_allowed_across_different_webinars(kommune):
    w1 = _make_webinar(slug="a")
    w2 = _make_webinar(slug="b")
    WebinarSignUp.objects.create(
        webinar=w1, kommune=kommune, school_name="A", participant_name="A", participant_email="x@y.dk"
    )
    WebinarSignUp.objects.create(
        webinar=w2, kommune=kommune, school_name="A", participant_name="A", participant_email="x@y.dk"
    )


@pytest.mark.django_db
def test_webinar_signup_clears_bounce_on_email_change(kommune):
    w = _make_webinar(slug="bn")
    s = WebinarSignUp.objects.create(
        webinar=w, kommune=kommune, school_name="A", participant_name="A", participant_email="old@example.com"
    )
    s.email_bounced_at = timezone.now()
    s.save()
    s.participant_email = "new@example.com"
    s.save()
    s.refresh_from_db()
    assert s.email_bounced_at is None


# ---------------------------------------------------------------------------
# Form
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_form_requires_all_four_fields(kommune):
    form = WebinarSignupForm(data={})
    assert not form.is_valid()
    for field in ["kommune", "school_name", "name", "email"]:
        assert field in form.errors


@pytest.mark.django_db
def test_form_accepts_complete_data(kommune):
    form = WebinarSignupForm(
        data={
            "kommune": kommune.pk,
            "school_name": "Skole X",
            "name": "Anna",
            "email": "a@b.dk",
        }
    )
    assert form.is_valid(), form.errors
    assert form.cleaned_data["kommune"] == kommune
    assert form.cleaned_data["school_name"] == "Skole X"


# ---------------------------------------------------------------------------
# Email senders
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_webinar_signup_context_includes_kommune_and_school(kommune):
    w = _make_webinar(slug="ctx")
    s = WebinarSignUp.objects.create(
        webinar=w, kommune=kommune, school_name="Skole X", participant_name="Anna", participant_email="a@b.dk"
    )
    ctx = get_webinar_signup_context(s)
    assert ctx["kommune"] == "Aarhus"
    assert ctx["school_name"] == "Skole X"
    assert ctx["meeting_url"] == w.meeting_url


@pytest.mark.django_db
def test_webinar_signup_context_meeting_url_blank_when_webinar_has_none(kommune):
    w = _make_webinar(slug="no-link", meeting_url="")
    s = WebinarSignUp.objects.create(
        webinar=w, kommune=kommune, school_name="X", participant_name="A", participant_email="a@b.dk"
    )
    ctx = get_webinar_signup_context(s)
    assert ctx["meeting_url"] == ""


@pytest.mark.django_db
def test_send_webinar_signup_confirmation_returns_true_in_dev_mode(kommune):
    w = _make_webinar(slug="cf")
    s = WebinarSignUp.objects.create(
        webinar=w, kommune=kommune, school_name="X", participant_name="A", participant_email="a@b.dk"
    )
    assert send_webinar_signup_confirmation(s) is True


@pytest.mark.django_db
def test_send_webinar_signup_notification_returns_true_in_dev_mode(kommune):
    w = _make_webinar(slug="nt")
    s = WebinarSignUp.objects.create(
        webinar=w, kommune=kommune, school_name="X", participant_name="A", participant_email="a@b.dk"
    )
    assert send_webinar_signup_notification(w, s) is True


# ---------------------------------------------------------------------------
# Public detail view
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_unpublished_webinar_returns_404():
    w = _make_webinar(slug="unpub")
    client = Client()
    resp = client.get(f"/webinar/{w.slug}/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_published_webinar_renders_form_and_info_box():
    w = _make_webinar(slug="open", is_published=True)
    client = Client()
    resp = client.get(f"/webinar/{w.slug}/")
    assert resp.status_code == 200
    assert b"Tilmeld" in resp.content
    assert "modtager en bekr".encode() in resp.content


@pytest.mark.django_db
def test_past_webinar_replaces_form_with_message():
    w = _make_webinar(slug="ended", start_at=timezone.now() - timedelta(days=1), is_published=True)
    client = Client()
    resp = client.get(f"/webinar/{w.slug}/")
    assert resp.status_code == 200
    assert b"har allerede fundet sted" in resp.content


@pytest.mark.django_db
def test_full_webinar_replaces_form_with_message(kommune):
    w = _make_webinar(slug="full", capacity=1, is_published=True)
    WebinarSignUp.objects.create(
        webinar=w, kommune=kommune, school_name="X", participant_name="A", participant_email="a@b.dk"
    )
    client = Client()
    resp = client.get(f"/webinar/{w.slug}/")
    assert b"Fuldt" in resp.content


@pytest.mark.django_db
def test_signup_creates_record_and_redirects(kommune):
    w = _make_webinar(slug="post", is_published=True)
    client = Client()
    resp = client.post(
        f"/webinar/{w.slug}/",
        {
            "kommune": kommune.pk,
            "school_name": "Skole X",
            "name": "Anna",
            "email": "a@b.dk",
        },
    )
    assert resp.status_code == 302
    assert resp.url == f"/webinar/{w.slug}/tak/"
    s = WebinarSignUp.objects.get(webinar=w)
    assert s.participant_name == "Anna"
    assert s.kommune_id == kommune.pk
    assert s.school_name == "Skole X"


@pytest.mark.django_db
def test_signup_rejects_duplicate_email(kommune):
    w = _make_webinar(slug="dup", is_published=True)
    WebinarSignUp.objects.create(
        webinar=w, kommune=kommune, school_name="X", participant_name="A", participant_email="dup@x.dk"
    )
    client = Client()
    resp = client.post(
        f"/webinar/{w.slug}/",
        {
            "kommune": kommune.pk,
            "school_name": "Skole X",
            "name": "B",
            "email": "dup@x.dk",
        },
    )
    assert resp.status_code == 200
    assert b"allerede tilmeldt" in resp.content


@pytest.mark.django_db
def test_success_page_renders():
    w = _make_webinar(slug="suc", is_published=True)
    client = Client()
    resp = client.get(f"/webinar/{w.slug}/tak/")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_client(db):
    User.objects.create_superuser("admin1", "admin1@x.dk", "pw")
    c = Client()
    c.login(username="admin1", password="pw")
    return c


@pytest.mark.django_db
def test_admin_list_page_loads(admin_client):
    resp = admin_client.get("/admin/webinars/webinar/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_signup_list_page_loads(admin_client):
    resp = admin_client.get("/admin/webinars/webinarsignup/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_manage_detail_requires_staff(kommune):
    """Anonymous and non-staff users must not see the admin detail page."""
    w = _make_webinar(slug="mng", is_published=True)
    client = Client()
    resp = client.get(f"/webinars/{w.pk}/")
    # Anonymous → redirected to login
    assert resp.status_code in (302, 403)


@pytest.mark.django_db
def test_manage_detail_shows_signups_and_copy_button(admin_client, kommune):
    w = _make_webinar(slug="mng2", is_published=True)
    WebinarSignUp.objects.create(
        webinar=w, kommune=kommune, school_name="Skole A", participant_name="Anna", participant_email="anna@x.dk"
    )
    WebinarSignUp.objects.create(
        webinar=w, kommune=kommune, school_name="Skole B", participant_name="Bo", participant_email="bo@y.dk"
    )
    resp = admin_client.get(f"/webinars/{w.pk}/")
    assert resp.status_code == 200
    body = resp.content.decode()
    # Both emails appear in the hidden field for the copy button to read
    assert 'id="all-emails"' in body
    assert "anna@x.dk" in body
    assert "bo@y.dk" in body
    # The button itself is rendered
    assert 'id="copy-emails-btn"' in body
    assert "Kopi" in body


@pytest.mark.django_db
def test_admin_can_publish_webinar_without_meeting_url(admin_client):
    """meeting_url is optional now — admin form must let publish go through."""
    resp = admin_client.post(
        "/admin/webinars/webinar/add/",
        {
            "title": "Without link",
            "slug": "no-link",
            "start_at_0": "2030-01-01",
            "start_at_1": "10:00:00",
            "duration_minutes": 60,
            "meeting_url": "",
            "is_published": "on",
            "instructors": [],
            "signups-TOTAL_FORMS": "0",
            "signups-INITIAL_FORMS": "0",
            "signups-MIN_NUM_FORMS": "0",
            "signups-MAX_NUM_FORMS": "1000",
        },
    )
    assert resp.status_code in (200, 302)
    assert Webinar.objects.filter(slug="no-link", is_published=True).exists()
