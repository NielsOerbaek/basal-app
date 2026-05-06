from datetime import timedelta

from django.db import models
from django.utils import timezone


class WebinarAccessMode(models.TextChoices):
    PUBLIC = "public", "Offentlig (alle kan tilmelde sig)"
    SCHOOL_GATED = "school_gated", "Kun tilmeldte skoler"


class Webinar(models.Model):
    title = models.CharField(max_length=255, verbose_name="Titel")
    slug = models.SlugField(max_length=255, unique=True, verbose_name="URL-slug")
    description = models.TextField(
        blank=True,
        verbose_name="Beskrivelse",
        help_text="HTML-tekst der vises på webinarets side",
    )
    intro_text = models.TextField(
        blank=True,
        verbose_name="Introtekst",
        help_text=(
            "HTML-tekst over formularen. Lad være tom for at bruge "
            "standardteksten fra Tilmeldingsside-indstillingen."
        ),
    )
    start_at = models.DateTimeField(verbose_name="Starttidspunkt")
    duration_minutes = models.PositiveIntegerField(default=60, verbose_name="Varighed (minutter)")
    meeting_url = models.URLField(
        verbose_name="Mødelink",
        help_text="Zoom/Teams/Meet-link — sendes i bekræftelsesmail, vises ikke offentligt",
    )
    instructors = models.ManyToManyField(
        "courses.Instructor",
        blank=True,
        related_name="webinars",
        verbose_name="Undervisere",
    )
    access_mode = models.CharField(
        max_length=20,
        choices=WebinarAccessMode.choices,
        default=WebinarAccessMode.PUBLIC,
        verbose_name="Adgang",
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
    registration_deadline = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Tilmeldingsfrist",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_at"]
        verbose_name = "Webinar"
        verbose_name_plural = "Webinarer"

    def __str__(self):
        return self.title

    @property
    def signup_count(self):
        return self.signups.count()

    @property
    def is_full(self):
        if self.capacity is None:
            return False
        if self.capacity == 0:
            return True
        return self.signup_count >= self.capacity

    @property
    def is_past(self):
        return self.start_at < timezone.now()

    @property
    def end_at(self):
        return self.start_at + timedelta(minutes=self.duration_minutes)
