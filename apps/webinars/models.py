from datetime import timedelta

from django.db import models
from django.urls import reverse
from django.utils import timezone


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


class WebinarSignUp(models.Model):
    webinar = models.ForeignKey(Webinar, on_delete=models.CASCADE, related_name="signups", verbose_name="Webinar")
    participant_name = models.CharField(max_length=255, verbose_name="Navn")
    participant_email = models.EmailField(verbose_name="E-mail")
    email_bounced_at = models.DateTimeField(null=True, blank=True, verbose_name="E-mail bouncet")
    participant_phone = models.CharField(max_length=50, blank=True, verbose_name="Telefon")
    participant_title = models.CharField(max_length=255, blank=True, verbose_name="Titel")
    organization = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Organisation",
        help_text="Hvor deltageren arbejder (valgfrit)",
    )
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
