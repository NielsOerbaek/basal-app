"""
Root-level pytest fixtures for the Basal application.
"""
from datetime import date, timedelta

import pytest
from django.contrib.auth.models import User
from django.test import Client

from apps.courses.models import Course
from apps.schools.models import School


@pytest.fixture(autouse=True)
def _disable_resend_emails(monkeypatch):
    """Prevent tests from sending real emails via Resend.

    The .env file contains a real RESEND_API_KEY which load_dotenv() loads
    into the environment. Patching resend.Emails.send directly is more
    robust than overriding settings, which doesn't apply to TestCase tests.
    """
    monkeypatch.setattr("resend.Emails.send", lambda params: {"id": "test_mock"})


@pytest.fixture
def staff_user(db):
    """Create a staff user."""
    return User.objects.create_user(
        username="staffuser",
        email="staff@test.com",
        password="testpass123",
        is_staff=True,
    )


@pytest.fixture
def superuser(db):
    """Create a superuser."""
    return User.objects.create_superuser(
        username="superuser",
        email="super@test.com",
        password="testpass123",
    )


@pytest.fixture
def staff_client(staff_user):
    """Return a test client logged in as staff user."""
    client = Client()
    client.login(username="staffuser", password="testpass123")
    return client


@pytest.fixture
def superuser_client(superuser):
    """Return a test client logged in as superuser."""
    client = Client()
    client.login(username="superuser", password="testpass123")
    return client


@pytest.fixture
def school_year(db):
    """Get the current school year (populated by migration)."""
    from apps.schools.school_years import get_current_school_year

    return get_current_school_year()


@pytest.fixture
def school(db):
    """Create a sample school."""
    return School.objects.create(
        name="Test School",
        adresse="Test Address 123",
        kommune="Test Kommune",
        enrolled_at=date.today() - timedelta(days=30),
    )


@pytest.fixture
def course(db):
    """Create a sample course."""
    return Course.objects.create(
        title="Test Course",
        start_date=date.today() + timedelta(days=7),
        end_date=date.today() + timedelta(days=7),
        location="Test Location",
        capacity=30,
    )
