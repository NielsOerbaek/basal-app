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
from apps.schools.models import Kommune, School
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


@pytest.fixture
def school(db, kommune):
    from datetime import date

    return School.objects.create(
        name="Skovvangskolen",
        adresse="Skovvangsvej 100",
        kommune=kommune,
        enrolled_at=date.today() - timedelta(days=30),
    )


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
def test_form_requires_kommune_school_name_email(kommune):
    """Empty form: kommune, school, name, email all flagged."""
    form = WebinarSignupForm(data={})
    assert not form.is_valid()
    for field in ["kommune", "name", "email"]:
        assert field in form.errors
    # school_name's "vælg en skole" message lands on school_name
    assert "school_name" in form.errors


@pytest.mark.django_db
def test_form_school_dropdown_populated_from_bound_kommune(kommune, school):
    """When the form is bound with a kommune, the school dropdown
    should contain that kommune's schools as choices."""
    form = WebinarSignupForm(data={"kommune": kommune.pk})
    choices = form.fields["school_name"].widget.choices
    school_names = [c[0] for c in choices if c[0]]
    assert school.name in school_names


@pytest.mark.django_db
def test_form_accepts_school_picked_from_kommune(kommune, school):
    form = WebinarSignupForm(
        data={
            "kommune": kommune.pk,
            "school_name": school.name,
            "name": "Anna",
            "email": "a@b.dk",
        }
    )
    assert form.is_valid(), form.errors
    assert form.cleaned_data["school_name"] == school.name


@pytest.mark.django_db
def test_form_rejects_school_not_in_chosen_kommune(kommune, school):
    other_kommune = Kommune.objects.create(name="København")
    form = WebinarSignupForm(
        data={
            "kommune": other_kommune.pk,
            "school_name": school.name,  # belongs to a different kommune
            "name": "Anna",
            "email": "a@b.dk",
        }
    )
    assert not form.is_valid()
    assert "school_name" in form.errors


@pytest.mark.django_db
def test_form_accepts_school_not_listed_with_other_text(kommune):
    form = WebinarSignupForm(
        data={
            "kommune": kommune.pk,
            "school_name": "",
            "school_not_listed": "on",
            "school_other": "En privat skole",
            "name": "Anna",
            "email": "a@b.dk",
        }
    )
    assert form.is_valid(), form.errors
    assert form.cleaned_data["school_name"] == "En privat skole"


@pytest.mark.django_db
def test_form_school_not_listed_requires_other_text(kommune):
    form = WebinarSignupForm(
        data={
            "kommune": kommune.pk,
            "school_not_listed": "on",
            "school_other": "",
            "name": "Anna",
            "email": "a@b.dk",
        }
    )
    assert not form.is_valid()
    assert "school_other" in form.errors


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
def test_signup_creates_record_and_redirects(kommune, school):
    w = _make_webinar(slug="post", is_published=True)
    client = Client()
    resp = client.post(
        f"/webinar/{w.slug}/",
        {
            "kommune": kommune.pk,
            "school_name": school.name,
            "name": "Anna",
            "email": "a@b.dk",
        },
    )
    assert resp.status_code == 302
    assert resp.url == f"/webinar/{w.slug}/tak/"
    s = WebinarSignUp.objects.get(webinar=w)
    assert s.participant_name == "Anna"
    assert s.kommune_id == kommune.pk
    assert s.school_name == school.name


@pytest.mark.django_db
def test_signup_with_other_school_creates_record(kommune):
    w = _make_webinar(slug="post-other", is_published=True)
    client = Client()
    resp = client.post(
        f"/webinar/{w.slug}/",
        {
            "kommune": kommune.pk,
            "school_not_listed": "on",
            "school_other": "Privat institut",
            "name": "Anna",
            "email": "a@b.dk",
        },
    )
    assert resp.status_code == 302
    s = WebinarSignUp.objects.get(webinar=w)
    assert s.school_name == "Privat institut"


@pytest.mark.django_db
def test_signup_rejects_duplicate_email(kommune, school):
    w = _make_webinar(slug="dup", is_published=True)
    WebinarSignUp.objects.create(
        webinar=w, kommune=kommune, school_name="X", participant_name="A", participant_email="dup@x.dk"
    )
    client = Client()
    resp = client.post(
        f"/webinar/{w.slug}/",
        {
            "kommune": kommune.pk,
            "school_name": school.name,
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
def test_manage_list_requires_staff():
    client = Client()
    resp = client.get("/webinars/")
    assert resp.status_code in (302, 403)


@pytest.mark.django_db
def test_manage_list_renders_for_staff(admin_client):
    _make_webinar(slug="a", title="Webinar A", is_published=True)
    _make_webinar(slug="b", title="Webinar B")
    resp = admin_client.get("/webinars/")
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "Webinar A" in body
    assert "Webinar B" in body
    assert "Tilføj webinar" in body


@pytest.mark.django_db
def test_manage_list_search_filters_by_title(admin_client):
    _make_webinar(slug="trivsel", title="Trivsel webinar")
    _make_webinar(slug="bevaegelse", title="Bevægelse webinar")
    resp = admin_client.get("/webinars/?search=Trivsel")
    body = resp.content.decode()
    assert "Trivsel webinar" in body
    assert "Bevægelse webinar" not in body


@pytest.mark.django_db
def test_create_form_renders(admin_client):
    resp = admin_client.get("/webinars/create/")
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "Tilføj webinar" in body
    assert 'name="title"' in body
    assert 'name="start_at"' in body


@pytest.mark.django_db
def test_create_post_creates_webinar_and_redirects(admin_client):
    resp = admin_client.post(
        "/webinars/create/",
        {
            "title": "Nyt webinar",
            "slug": "",  # auto-generated server-side from title
            "description": "<p>Hej</p>",
            "start_at": "2030-06-01T10:00",
            "duration_minutes": 60,
            "meeting_url": "",
            "capacity": "",
            "is_published": "on",
            "instructor_1": "",
            "instructor_2": "",
            "instructor_3": "",
            "new_instructor_1": "",
            "new_instructor_2": "",
            "new_instructor_3": "",
        },
    )
    assert resp.status_code == 302
    w = Webinar.objects.get(title="Nyt webinar")
    assert w.slug == "nyt-webinar"  # auto-generated
    assert w.is_published is True
    assert resp.url == f"/webinars/{w.pk}/"


@pytest.mark.django_db
def test_update_form_pre_populates_and_saves(admin_client):
    w = _make_webinar(slug="old", title="Gammel titel")
    resp = admin_client.get(f"/webinars/{w.pk}/edit/")
    assert resp.status_code == 200
    assert b"Gammel titel" in resp.content

    resp = admin_client.post(
        f"/webinars/{w.pk}/edit/",
        {
            "title": "Ny titel",
            "slug": "old",
            "description": "",
            "start_at": w.start_at.strftime("%Y-%m-%dT%H:%M"),
            "duration_minutes": w.duration_minutes,
            "meeting_url": w.meeting_url,
            "capacity": "",
            "instructor_1": "",
            "instructor_2": "",
            "instructor_3": "",
            "new_instructor_1": "",
            "new_instructor_2": "",
            "new_instructor_3": "",
        },
    )
    assert resp.status_code == 302
    w.refresh_from_db()
    assert w.title == "Ny titel"


@pytest.mark.django_db
def test_create_with_new_instructor_creates_instructor_record(admin_client):
    from apps.courses.models import Instructor

    resp = admin_client.post(
        "/webinars/create/",
        {
            "title": "Webinar with new instructor",
            "slug": "wwni",
            "description": "",
            "start_at": "2030-06-01T10:00",
            "duration_minutes": 60,
            "meeting_url": "",
            "capacity": "",
            "instructor_1": "__new__",
            "new_instructor_1": "Helle Helt",
            "instructor_2": "",
            "instructor_3": "",
            "new_instructor_2": "",
            "new_instructor_3": "",
        },
    )
    assert resp.status_code == 302
    assert Instructor.objects.filter(name="Helle Helt").exists()
    w = Webinar.objects.get(slug="wwni")
    assert w.instructors.filter(name="Helle Helt").exists()


@pytest.mark.django_db
def test_delete_get_renders_confirm_modal(admin_client):
    w = _make_webinar(slug="del")
    resp = admin_client.get(f"/webinars/{w.pk}/delete/")
    assert resp.status_code == 200
    assert b"Slet webinar permanent" in resp.content


@pytest.mark.django_db
def test_delete_post_removes_webinar(admin_client):
    w = _make_webinar(slug="del2")
    resp = admin_client.post(f"/webinars/{w.pk}/delete/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["redirect"] == "/webinars/"
    assert not Webinar.objects.filter(pk=w.pk).exists()


@pytest.mark.django_db
def test_signup_delete_get_renders_confirm_modal(admin_client, kommune):
    w = _make_webinar(slug="sd1")
    s = WebinarSignUp.objects.create(
        webinar=w, kommune=kommune, school_name="Skole", participant_name="Anna", participant_email="anna@x.dk"
    )
    resp = admin_client.get(f"/webinars/signups/{s.pk}/delete/")
    assert resp.status_code == 200
    assert b"Anna" in resp.content


@pytest.mark.django_db
def test_signup_delete_post_removes_signup_and_redirects_to_manage(admin_client, kommune):
    w = _make_webinar(slug="sd2")
    s = WebinarSignUp.objects.create(
        webinar=w, kommune=kommune, school_name="Skole", participant_name="Bo", participant_email="bo@x.dk"
    )
    resp = admin_client.post(f"/webinars/signups/{s.pk}/delete/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["redirect"] == f"/webinars/{w.pk}/"
    assert not WebinarSignUp.objects.filter(pk=s.pk).exists()


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
