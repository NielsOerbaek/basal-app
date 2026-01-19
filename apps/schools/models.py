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


class SchoolYearManager(models.Manager):
    def get_current(self):
        """Hent det aktuelle skoleår baseret på dags dato."""
        today = date.today()
        return self.filter(start_date__lte=today, end_date__gte=today).first()


class SchoolYear(models.Model):
    name = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Skoleår',
        help_text='F.eks. "2024-2025"'
    )
    start_date = models.DateField(
        verbose_name='Startdato',
        help_text='Typisk 1. august'
    )
    end_date = models.DateField(
        verbose_name='Slutdato',
        help_text='Typisk 31. juli'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = SchoolYearManager()

    class Meta:
        ordering = ['start_date']
        verbose_name = 'Skoleår'
        verbose_name_plural = 'Skoleår'

    def __str__(self):
        return self.name

    @property
    def is_current(self):
        """Udregnes dynamisk baseret på dags dato."""
        today = date.today()
        return self.start_date <= today <= self.end_date

    def get_enrolled_schools(self):
        """Hent alle skoler der var tilmeldt i dette skoleår."""
        # Tilmeldt hvis: enrolled_at <= end_date OG (ikke frameldt ELLER frameldt efter start_date)
        from django.db.models import Q
        return School.objects.active().filter(
            enrolled_at__isnull=False,
            enrolled_at__lte=self.end_date
        ).filter(
            Q(opted_out_at__isnull=True) | Q(opted_out_at__gt=self.start_date)
        )

    @property
    def enrolled_schools_count(self):
        """Antal skoler tilmeldt i dette skoleår."""
        return self.get_enrolled_schools().count()


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
    opted_out_at = models.DateField(
        null=True,
        blank=True,
        verbose_name='Frameldt dato',
        help_text='Dato for framelding fra Basal (permanent)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SchoolManager()

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active', 'name']),
            models.Index(fields=['kommune']),
            models.Index(fields=['is_active', 'kommune']),
        ]

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        self.is_active = False
        self.save()

    @property
    def is_enrolled(self):
        """Tjek om skolen er tilmeldt Basal."""
        return self.enrolled_at is not None and self.opted_out_at is None

    @property
    def is_opted_out(self):
        """Tjek om skolen har frameldt sig."""
        return self.opted_out_at is not None

    def was_enrolled_in_year(self, school_year):
        """Tjek om skolen var tilmeldt i et givent skoleår."""
        if not self.enrolled_at:
            return False
        # Tilmeldt hvis enrolled_at <= year.end_date OG (ikke frameldt ELLER frameldt efter year.start_date)
        if self.enrolled_at > school_year.end_date:
            return False
        if self.opted_out_at and self.opted_out_at <= school_year.start_date:
            return False
        return True

    def get_enrolled_years(self):
        """Hent alle skoleår skolen var/er tilmeldt i."""
        if not self.enrolled_at:
            return SchoolYear.objects.none()
        qs = SchoolYear.objects.filter(end_date__gte=self.enrolled_at)
        if self.opted_out_at:
            qs = qs.filter(start_date__lt=self.opted_out_at)
        return qs

    def get_enrollment_history(self):
        """
        Hent historik over til- og frameldinger fra ActivityLog.
        Returnerer en liste af dicts med 'date', 'event_type' ('enrolled'/'opted_out'), og 'label'.
        """
        from apps.audit.models import ActivityLog
        from django.contrib.contenttypes.models import ContentType
        from datetime import datetime

        history = []
        school_ct = ContentType.objects.get_for_model(School)

        # Hent alle ændringer til denne skole
        logs = ActivityLog.objects.filter(
            content_type=school_ct,
            object_id=self.pk
        ).order_by('timestamp')

        for log in logs:
            changes = log.changes or {}

            # Tjek for ændring af enrolled_at
            if 'enrolled_at' in changes:
                old_val = changes['enrolled_at'].get('old')
                new_val = changes['enrolled_at'].get('new')
                if new_val and not old_val:
                    # Ny tilmelding
                    history.append({
                        'date': datetime.strptime(new_val, '%Y-%m-%d').date(),
                        'event_type': 'enrolled',
                        'label': 'Tilmeldt',
                    })

            # Tjek for ændring af opted_out_at
            if 'opted_out_at' in changes:
                old_val = changes['opted_out_at'].get('old')
                new_val = changes['opted_out_at'].get('new')
                if new_val and not old_val:
                    # Framelding
                    history.append({
                        'date': datetime.strptime(new_val, '%Y-%m-%d').date(),
                        'event_type': 'opted_out',
                        'label': 'Frameldt',
                    })
                elif old_val and not new_val:
                    # Fjernelse af framelding = gentilmelding
                    history.append({
                        'date': log.timestamp.date(),
                        'event_type': 'enrolled',
                        'label': 'Tilmeldt igen',
                    })

        # Hvis ingen historik men skolen har enrolled_at, tilføj det som første event
        if not history and self.enrolled_at:
            history.append({
                'date': self.enrolled_at,
                'event_type': 'enrolled',
                'label': 'Tilmeldt',
            })
            if self.opted_out_at:
                history.append({
                    'date': self.opted_out_at,
                    'event_type': 'opted_out',
                    'label': 'Frameldt',
                })

        # Sortér efter dato
        history.sort(key=lambda x: x['date'])
        return history

    @property
    def base_seats(self):
        """Base seats included with enrollment."""
        return self.BASE_SEATS if self.is_enrolled else 0

    @property
    def has_forankringsplads(self):
        """School gets forankringsplads after 1 year of enrollment."""
        if not self.enrolled_at:
            return False
        one_year_ago = date.today() - timezone.timedelta(days=365)
        return self.enrolled_at <= one_year_ago

    @property
    def forankring_seats(self):
        """Forankringsplads seats (1 if enrolled > 1 year and currently enrolled)."""
        if not self.is_enrolled:
            return 0
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
    school_years = models.ManyToManyField(
        SchoolYear,
        related_name='invoices',
        verbose_name='Skoleår',
        blank=True
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


