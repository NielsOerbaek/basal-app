"""
Root-level pytest fixtures for the Basal application.
"""
from datetime import date, timedelta

import pytest
from django.contrib.auth.models import User
from django.test import Client

from apps.courses.models import Course
from apps.schools.models import School, SchoolYear


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
    """Create a current school year."""
    today = date.today()
    # Create a school year that spans the current date
    if today.month >= 8:
        start = date(today.year, 8, 1)
        end = date(today.year + 1, 7, 31)
        name = f"{today.year}-{today.year + 1}"
    else:
        start = date(today.year - 1, 8, 1)
        end = date(today.year, 7, 31)
        name = f"{today.year - 1}-{today.year}"

    school_year, _ = SchoolYear.objects.get_or_create(
        name=name,
        defaults={"start_date": start, "end_date": end},
    )
    return school_year


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
