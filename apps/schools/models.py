from datetime import date

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class PersonRole(models.TextChoices):
    KOORDINATOR = 'koordinator', 'Koordinator'
    SKOLELEDER = 'skoleleder', 'Skoleleder'
    UDSKOLINGSLEDER = 'udskolingsleder', 'Udskolingsleder'
    OTHER = 'other', 'Andet'


class InvoiceStatus(models.TextChoices):
    PLANNED = 'planned', 'Planlagt'
    SENT = 'sent', 'Sendt'
    PAID = 'paid', 'Betalt'


class SchoolManager(models.Manager):
    def active(self):
        return self.filter(is_active=True)


class School(models.Model):
    BASE_SEATS = 3
    FORANKRING_SEATS = 1

    name = models.CharField(max_length=255, verbose_name='Navn')
    adresse = models.CharField(max_length=255, verbose_name='Adresse')
    kommune = models.CharField(max_length=100, verbose_name='Kommune')
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


class Person(models.Model):
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='people'
    )
    name = models.CharField(max_length=255, verbose_name='Navn')
    role = models.CharField(
        max_length=20,
        choices=PersonRole.choices,
        default=PersonRole.KOORDINATOR,
        verbose_name='Funktion'
    )
    role_other = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Anden funktion'
    )
    phone = models.CharField(max_length=50, blank=True, verbose_name='Telefon')
    email = models.EmailField(blank=True, verbose_name='E-mail')
    comment = models.TextField(blank=True, verbose_name='Kommentar')
    is_primary = models.BooleanField(default=False, verbose_name='Primær kontakt')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', 'name']
        verbose_name = 'Person'
        verbose_name_plural = 'Personer'

    def __str__(self):
        return f"{self.name} ({self.display_role})"

    @property
    def display_role(self):
        if self.role == PersonRole.OTHER:
            return self.role_other or 'Andet'
        return self.get_role_display()


class SchoolComment(models.Model):
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='school_comments'
    )
    comment = models.TextField(verbose_name='Kommentar')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='school_comments_made'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Kommentar'
        verbose_name_plural = 'Kommentarer'

    def __str__(self):
        return f"{self.school.name} - {self.created_at.strftime('%Y-%m-%d')}"


class Invoice(models.Model):
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='invoices'
    )
    invoice_number = models.CharField(
        max_length=50,
        verbose_name='Fakturanummer'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Beløb'
    )
    status = models.CharField(
        max_length=10,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.PLANNED,
        verbose_name='Status'
    )
    date = models.DateField(
        default=date.today,
        verbose_name='Dato'
    )
    comment = models.TextField(
        blank=True,
        verbose_name='Kommentar'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name = 'Faktura'
        verbose_name_plural = 'Fakturaer'

    def __str__(self):
        return f"{self.invoice_number} - {self.school.name}"
