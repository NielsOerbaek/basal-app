from datetime import date

from django.db import models
from django.utils import timezone


class SchoolManager(models.Manager):
    def active(self):
        return self.filter(is_active=True)


class School(models.Model):
    BASE_SEATS = 3
    FORANKRING_SEATS = 1

    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=255)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=50, blank=True)
    comments = models.TextField(blank=True)
    enrolled_at = models.DateField(
        null=True,
        blank=True,
        verbose_name='Tilmeldt dato',
        help_text='Dato for skolens tilmelding til Basal'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SchoolManager()

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        self.is_active = False
        self.save()

    @property
    def base_seats(self):
        """Base seats included with enrollment."""
        return self.BASE_SEATS if self.enrolled_at else 0

    @property
    def has_forankringsplads(self):
        """School gets forankringsplads after 1 year of enrollment."""
        if not self.enrolled_at:
            return False
        one_year_ago = date.today() - timezone.timedelta(days=365)
        return self.enrolled_at <= one_year_ago

    @property
    def forankring_seats(self):
        """Forankringsplads seats (1 if enrolled > 1 year)."""
        return self.FORANKRING_SEATS if self.has_forankringsplads else 0

    @property
    def purchased_seats(self):
        """Total additional seats purchased."""
        return self.seat_purchases.aggregate(
            total=models.Sum('seats')
        )['total'] or 0

    @property
    def total_seats(self):
        """Total seats available to the school."""
        return self.base_seats + self.forankring_seats + self.purchased_seats

    @property
    def used_seats(self):
        """Number of seats used (all course signups)."""
        return self.course_signups.count()

    @property
    def remaining_seats(self):
        """Number of seats remaining."""
        return max(0, self.total_seats - self.used_seats)

    @property
    def has_available_seats(self):
        """Check if school has available seats for signup."""
        return self.remaining_seats > 0


class SeatPurchase(models.Model):
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='seat_purchases'
    )
    seats = models.PositiveIntegerField(
        verbose_name='Antal pladser'
    )
    purchased_at = models.DateField(
        default=date.today,
        verbose_name='Købsdato'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Noter'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-purchased_at']

    def __str__(self):
        return f"{self.school.name} - {self.seats} pladser ({self.purchased_at})"
