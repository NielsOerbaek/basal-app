from datetime import timedelta

from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format


class Webinar(models.Model):
    title = models.CharField(max_length=255, verbose_name="Titel")
    slug = models.SlugField(max_length=255, unique=True, verbose_name="URL-slug")
    description = models.TextField(
        blank=True,
        verbose_name="Beskrivelse",
        help_text="HTML-tekst der vises på webinarets side over metadata-kortet",
    )
    start_at = models.DateTimeField(verbose_name="Starttidspunkt")
    duration_minutes = models.PositiveIntegerField(default=60, verbose_name="Varighed (minutter)")
    meeting_url = models.URLField(
        blank=True,
        verbose_name="Mødelink",
        help_text=(
            "Zoom/Teams/Meet-link — sendes til deltagerne i bekræftelsesmailen. "
            "Hvis feltet er tomt, oplyses deltageren om at linket eftersendes tættere på datoen."
        ),
    )
    instructors = models.ManyToManyField(
        "courses.Instructor",
        blank=True,
        related_name="webinars",
        verbose_name="Oplægsholdere",
    )
    capacity = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Kapacitet",
        help_text="Lad være tom for ubegrænset",
    )
    is_published = models.BooleanField(
        default=False,
        verbose_name="Offentliggjort",
        help_text="Offentliggjorte webinarer er synlige på deres URL",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_at"]
        verbose_name = "Webinar"
        verbose_name_plural = "Webinarer"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("webinar:detail", args=[self.slug])

    @property
    def signup_count(self):
        return self.signups.count()

    @property
    def is_full(self):
        if self.capacity is None:
            return False
        return self.signup_count >= self.capacity

    @property
    def is_past(self):
        return self.start_at < timezone.now()

    @property
    def end_at(self):
        return self.start_at + timedelta(minutes=self.duration_minutes)

    @property
    def display_time(self):
        """Combined date + start/end time + duration, e.g.
        '12. oktober 2026 18:00 - 19:30 (90 minutter)'.

        Localized to the project timezone — `start_at` is stored in UTC,
        and `date_format` does NOT auto-localize, so we convert first.
        """
        local_start = timezone.localtime(self.start_at)
        local_end = timezone.localtime(self.end_at)
        date_str = date_format(local_start, "j. F Y")
        start_str = date_format(local_start, "H:i")
        end_str = date_format(local_end, "H:i")
        return f"{date_str} {start_str} - {end_str} ({self.duration_minutes} minutter)"


class WebinarSignUp(models.Model):
    webinar = models.ForeignKey(Webinar, on_delete=models.CASCADE, related_name="signups", verbose_name="Webinar")
    kommune = models.ForeignKey(
        "schools.Kommune",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="webinar_signups",
        verbose_name="Kommune",
    )
    school_name = models.CharField(max_length=255, blank=True, verbose_name="Skole")
    participant_name = models.CharField(max_length=255, verbose_name="Navn")
    participant_email = models.EmailField(verbose_name="E-mail")
    email_bounced_at = models.DateTimeField(null=True, blank=True, verbose_name="E-mail bouncet")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["webinar", "participant_name"]
        verbose_name = "Webinartilmelding"
        verbose_name_plural = "Webinartilmeldinger"
        constraints = [
            models.UniqueConstraint(
                fields=["webinar", "participant_email"],
                name="webinarsignup_unique_email_per_webinar",
            ),
        ]

    def __str__(self):
        return f"{self.participant_name} ({self.webinar.title})"

    def save(self, *args, **kwargs):
        if self.pk:
            old_email = WebinarSignUp.objects.filter(pk=self.pk).values_list("participant_email", flat=True).first()
            if old_email and old_email != self.participant_email:
                self.email_bounced_at = None
        super().save(*args, **kwargs)
