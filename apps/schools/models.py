from datetime import date

from django.contrib.auth.models import User
from django.db import models


class TitelChoice(models.TextChoices):
    SKOLELEDER = "skoleleder", "Skoleleder"
    UDSKOLINGSLEDER = "udskolingsleder", "Udskolingsleder"
    KLASSELAERER = "klasselaerer", "Klasselærer"
    PAEDAGOG = "paedagog", "Pædagog"
    AKT_INKLUSIONSVEJLEDER = "akt_inklusionsvejleder", "AKT/inklusionsvejleder"
    TRIVSELSVEJLEDER = "trivselsvejleder", "Trivselsvejleder"
    ANDET = "andet", "Andet"


class InvoiceStatus(models.TextChoices):
    PLANNED = "planned", "Planlagt"
    SENT = "sent", "Sendt"
    PAID = "paid", "Betalt"


class SchoolYearManager(models.Manager):
    def get_current(self):
        """Hent det aktuelle skoleår baseret på dags dato."""
        today = date.today()
        return self.filter(start_date__lte=today, end_date__gte=today).first()


class SchoolYear(models.Model):
    name = models.CharField(max_length=20, unique=True, verbose_name="Skoleår", help_text='F.eks. "2024/25"')
    start_date = models.DateField(verbose_name="Startdato", help_text="Typisk 1. august")
    end_date = models.DateField(verbose_name="Slutdato", help_text="Typisk 31. juli")
    created_at = models.DateTimeField(auto_now_add=True)

    objects = SchoolYearManager()

    class Meta:
        ordering = ["start_date"]
        verbose_name = "Skoleår"
        verbose_name_plural = "Skoleår"

    def __str__(self):
        return self.name

    @property
    def is_current(self):
        """Udregnes dynamisk baseret på dags dato."""
        today = date.today()
        return self.start_date <= today <= self.end_date

    def get_enrolled_schools(self):
        """Hent alle skoler der var tilmeldt i dette skoleår."""
        # Tilmeldt hvis: active_from <= end_date OG (ikke frameldt ELLER frameldt efter start_date)
        from django.db.models import Q

        return (
            School.objects.active()
            .filter(active_from__isnull=False, active_from__lte=self.end_date)
            .filter(Q(opted_out_at__isnull=True) | Q(opted_out_at__gt=self.start_date))
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

    name = models.CharField(max_length=255, verbose_name="Navn")
    adresse = models.CharField(max_length=255, verbose_name="Adresse")
    postnummer = models.CharField(max_length=4, blank=True, verbose_name="Postnummer")
    by = models.CharField(max_length=100, blank=True, verbose_name="By")
    kommune = models.CharField(max_length=100, verbose_name="Kommune")
    ean_nummer = models.CharField(max_length=13, blank=True, verbose_name="EAN-nummer")

    # Billing fields (when municipality pays)
    kommunen_betaler = models.BooleanField(default=False, verbose_name="Kommunen betaler")
    fakturering_adresse = models.CharField(max_length=255, blank=True, verbose_name="Faktureringsadresse")
    fakturering_postnummer = models.CharField(max_length=4, blank=True, verbose_name="Postnummer")
    fakturering_by = models.CharField(max_length=100, blank=True, verbose_name="By")
    fakturering_ean_nummer = models.CharField(max_length=13, blank=True, verbose_name="EAN-nummer")
    fakturering_kontakt_navn = models.CharField(max_length=255, blank=True, verbose_name="Kontaktperson")
    fakturering_kontakt_email = models.EmailField(blank=True, verbose_name="E-mail")

    enrolled_at = models.DateField(
        null=True, blank=True, verbose_name="Tilmeldt dato", help_text="Dato for skolens tilmelding til Basal"
    )
    active_from = models.DateField(
        null=True,
        blank=True,
        verbose_name="Aktiv fra",
        help_text="Dato hvor tilmeldingen træder i kraft (påvirker pladser og forankring)",
    )
    is_active = models.BooleanField(default=True)
    opted_out_at = models.DateField(
        null=True, blank=True, verbose_name="Frameldt dato", help_text="Dato for framelding fra Basal (permanent)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    signup_password = models.CharField(
        max_length=25, blank=True, verbose_name="Tilmeldingskode", help_text="Kode til kursustilmelding"
    )
    signup_token = models.CharField(
        max_length=32, blank=True, db_index=True, verbose_name="Tilmeldingstoken", help_text="Token til direkte link"
    )

    objects = SchoolManager()

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_active", "name"]),
            models.Index(fields=["kommune"]),
            models.Index(fields=["is_active", "kommune"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["name", "kommune"], name="unique_school_per_kommune"),
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

    @property
    def enrollment_status(self):
        """
        Returnerer skolens detaljerede tilmeldingsstatus for det aktuelle skoleår.
        Returns tuple: (status_code, status_label, badge_class)
        """
        from apps.schools.school_years import get_current_school_year

        return self.get_status_for_year(get_current_school_year().name)

    def was_enrolled_in_year(self, school_year):
        """Tjek om skolen var tilmeldt i et givent skoleår."""
        if not self.active_from:
            return False
        # Tilmeldt hvis active_from <= year.end_date OG (ikke frameldt ELLER frameldt efter year.start_date)
        if self.active_from > school_year.end_date:
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
        from datetime import datetime

        from django.contrib.contenttypes.models import ContentType

        from apps.audit.models import ActivityLog

        history = []
        school_ct = ContentType.objects.get_for_model(School)

        # Hent alle ændringer til denne skole
        logs = ActivityLog.objects.filter(content_type=school_ct, object_id=self.pk).order_by("timestamp")

        for log in logs:
            changes = log.changes or {}

            # Tjek for ændring af enrolled_at
            if "enrolled_at" in changes:
                old_val = changes["enrolled_at"].get("old")
                new_val = changes["enrolled_at"].get("new")
                if new_val and not old_val:
                    # Ny tilmelding
                    history.append(
                        {
                            "date": datetime.strptime(new_val, "%Y-%m-%d").date(),
                            "event_type": "enrolled",
                            "label": "Tilmeldt",
                        }
                    )

            # Tjek for ændring af opted_out_at
            if "opted_out_at" in changes:
                old_val = changes["opted_out_at"].get("old")
                new_val = changes["opted_out_at"].get("new")
                if new_val and not old_val:
                    # Framelding
                    history.append(
                        {
                            "date": datetime.strptime(new_val, "%Y-%m-%d").date(),
                            "event_type": "opted_out",
                            "label": "Frameldt",
                        }
                    )
                elif old_val and not new_val:
                    # Fjernelse af framelding = gentilmelding
                    history.append(
                        {
                            "date": log.timestamp.date(),
                            "event_type": "enrolled",
                            "label": "Tilmeldt igen",
                        }
                    )

        # Hvis ingen historik men skolen har enrolled_at, tilføj det som første event
        if not history and self.enrolled_at:
            history.append(
                {
                    "date": self.enrolled_at,
                    "event_type": "enrolled",
                    "label": "Tilmeldt",
                }
            )
            if self.opted_out_at:
                history.append(
                    {
                        "date": self.opted_out_at,
                        "event_type": "opted_out",
                        "label": "Frameldt",
                    }
                )

        # Sortér efter dato
        history.sort(key=lambda x: x["date"])
        return history

    @property
    def base_seats(self):
        """Base seats included with enrollment."""
        if not self.is_enrolled:
            return 0
        # Check if active_from is set and not in the future
        if self.active_from and self.active_from > date.today():
            return 0
        return self.BASE_SEATS

    @property
    def has_forankringsplads(self):
        """School gets forankringsplads if active_from is before current school year."""
        if not self.active_from:
            return False
        from apps.schools.school_years import get_current_school_year

        try:
            current_year = get_current_school_year()
            return self.active_from < current_year.start_date
        except SchoolYear.DoesNotExist:
            return False

    def get_status_for_year(self, year_str: str) -> tuple[str, str, str]:
        """
        Get school status for a specific school year.

        Args:
            year_str: School year in format '2024/25' or '2024-25'

        Returns:
            Tuple of (status_code, status_label, badge_class)
        """
        from apps.schools.school_years import get_school_year_dates, normalize_school_year

        year_str = normalize_school_year(year_str)
        start_date, end_date = get_school_year_dates(year_str)

        # Check if opted out before or during this year
        if self.opted_out_at and self.opted_out_at <= end_date:
            if self.opted_out_at <= start_date:
                return ("frameldt", "Frameldt", "bg-secondary")
            # Opted out during the year - still count as enrolled for that year
            pass

        # Not enrolled at all, or active after this year
        if not self.active_from or self.active_from > end_date:
            return ("ikke_tilmeldt", "Ikke tilmeldt", "bg-warning text-dark")

        # Enrolled - check if new or anchoring for this year
        if self.active_from >= start_date:
            # Active during this school year = new
            return ("tilmeldt_ny", "Tilmeldt (ny)", "bg-success")
        else:
            # Active before this school year = anchoring
            return ("tilmeldt_forankring", "Tilmeldt (forankring)", "bg-primary")

    @property
    def forankring_seats(self):
        """Forankringsplads seats (1 if enrolled > 1 year and currently enrolled)."""
        if not self.is_enrolled:
            return 0
        return self.FORANKRING_SEATS if self.has_forankringsplads else 0

    @property
    def purchased_seats(self):
        """Total additional seats purchased."""
        return self.seat_purchases.aggregate(total=models.Sum("seats"))["total"] or 0

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

    @property
    def exceeds_seat_allocation(self):
        """Check if school is using more seats than allocated (needs additional invoice)."""
        return self.used_seats > self.total_seats

    def generate_credentials(self):
        """Generate signup password and token for this school."""
        from apps.schools.utils import generate_pronounceable_password, generate_signup_token

        self.signup_password = generate_pronounceable_password()
        self.signup_token = generate_signup_token()
        self.save(update_fields=["signup_password", "signup_token"])


class SeatPurchase(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="seat_purchases")
    seats = models.PositiveIntegerField(verbose_name="Antal pladser")
    purchased_at = models.DateField(default=date.today, verbose_name="Købsdato")
    notes = models.TextField(blank=True, verbose_name="Noter")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-purchased_at"]

    def __str__(self):
        return f"{self.school.name} - {self.seats} pladser ({self.purchased_at})"


class Person(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="people")
    name = models.CharField(max_length=255, verbose_name="Navn")
    titel = models.CharField(max_length=30, choices=TitelChoice.choices, blank=True, verbose_name="Titel")
    titel_other = models.CharField(max_length=100, blank=True, verbose_name="Anden titel")
    phone = models.CharField(max_length=50, blank=True, verbose_name="Telefon")
    email = models.EmailField(blank=True, verbose_name="E-mail")
    comment = models.TextField(blank=True, verbose_name="Kommentar")
    is_koordinator = models.BooleanField(default=False, verbose_name="Koordinator")
    is_oekonomisk_ansvarlig = models.BooleanField(default=False, verbose_name="Økonomisk ansvarlig")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_koordinator", "-is_oekonomisk_ansvarlig", "name"]
        verbose_name = "Person"
        verbose_name_plural = "Personer"

    def __str__(self):
        roles = ", ".join(self.roles) if self.roles else "Ingen rolle"
        return f"{self.name} ({roles})"

    @property
    def display_titel(self):
        if self.titel == TitelChoice.ANDET:
            return self.titel_other or "Andet"
        if self.titel:
            return self.get_titel_display()
        return ""

    @property
    def roles(self):
        """Return list of role labels for chip display."""
        result = []
        if self.is_koordinator:
            result.append("Koordinator")
        if self.is_oekonomisk_ansvarlig:
            result.append("Økonomisk ansvarlig")
        return result


class SchoolComment(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="school_comments")
    comment = models.TextField(verbose_name="Kommentar")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="school_comments_made")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Kommentar"
        verbose_name_plural = "Kommentarer"

    def __str__(self):
        return f"{self.school.name} - {self.created_at.strftime('%Y-%m-%d')}"


class Invoice(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="invoices")
    school_year = models.ForeignKey(
        SchoolYear,
        on_delete=models.PROTECT,
        related_name="invoices",
        verbose_name="Skoleår",
        null=True,
        blank=True,
    )
    invoice_number = models.CharField(max_length=50, verbose_name="Fakturanummer")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Beløb")
    status = models.CharField(
        max_length=10, choices=InvoiceStatus.choices, default=InvoiceStatus.PLANNED, verbose_name="Status"
    )
    date = models.DateField(default=date.today, verbose_name="Dato")
    comment = models.TextField(blank=True, verbose_name="Kommentar")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        verbose_name = "Faktura"
        verbose_name_plural = "Fakturaer"
        constraints = [
            models.UniqueConstraint(
                fields=["invoice_number", "school_year"],
                name="unique_invoice_per_school_year",
            ),
        ]

    def __str__(self):
        return f"{self.invoice_number} - {self.school.name}"


class SchoolFile(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to="school_files/%Y/%m/", verbose_name="Fil")
    description = models.TextField(blank=True, verbose_name="Beskrivelse")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="school_files_uploaded")

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Skolefil"
        verbose_name_plural = "Skolefiler"

    def __str__(self):
        return f"{self.school.name} - {self.filename}"

    @property
    def filename(self):
        if not self.file:
            return ""
        return self.file.name.split("/")[-1]
