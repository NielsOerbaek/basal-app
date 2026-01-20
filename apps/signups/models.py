from django.contrib.auth.models import User
from django.db import models


class SignupPageType(models.TextChoices):
    COURSE_SIGNUP = "course_signup", "Kursustilmelding"
    SCHOOL_SIGNUP = "school_signup", "Skoletilmelding"


class SignupPage(models.Model):
    """Admin-editable content for signup pages."""

    page_type = models.CharField(max_length=20, unique=True, choices=SignupPageType.choices, verbose_name="Sidetype")
    title = models.CharField(max_length=255, verbose_name="Overskrift")
    subtitle = models.CharField(max_length=255, blank=True, verbose_name="Underoverskrift")
    intro_text = models.TextField(
        blank=True, verbose_name="Introtekst", help_text="HTML-tekst der vises over formularen"
    )
    success_title = models.CharField(max_length=255, verbose_name="Succesoverskrift")
    success_message = models.TextField(
        verbose_name="Succesbesked", help_text="HTML-tekst der vises efter vellykket tilmelding"
    )
    submit_button_text = models.CharField(max_length=50, default="Tilmeld", verbose_name="Knaptekst")
    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktiv",
        help_text="Deaktiverede sider viser en besked om at tilmelding ikke er mulig",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tilmeldingsside"
        verbose_name_plural = "Tilmeldingssider"

    def __str__(self):
        return self.get_page_type_display()


class FieldType(models.TextChoices):
    CHECKBOX = "checkbox", "Afkrydsningsfelt"


class SignupFormField(models.Model):
    """Dynamic form fields that can be added to signup pages."""

    signup_page = models.ForeignKey(
        SignupPage, on_delete=models.CASCADE, related_name="form_fields", verbose_name="Tilmeldingsside"
    )
    field_type = models.CharField(max_length=20, choices=FieldType.choices, verbose_name="Felttype")
    label = models.CharField(
        max_length=500, verbose_name="Label", help_text="Feltnavn/tekst (HTML tilladt)"
    )
    help_text = models.CharField(max_length=500, blank=True, verbose_name="Hjælpetekst")
    is_required = models.BooleanField(default=True, verbose_name="Påkrævet")
    attachment = models.FileField(
        upload_to="signup_attachments/",
        blank=True,
        verbose_name="Vedhæftet fil",
        help_text="Dokument som brugeren kan downloade (f.eks. vilkår og betingelser)",
    )
    order = models.PositiveIntegerField(default=0, verbose_name="Rækkefølge")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Formularfelt"
        verbose_name_plural = "Formularfelter"

    def __str__(self):
        return f"{self.get_field_type_display()}: {self.label[:50]}"

    @property
    def field_name(self):
        """Generate a unique field name for form usage."""
        return f"custom_{self.field_type}_{self.pk}"


class SchoolSignup(models.Model):
    """School applications to join the Basal project."""

    # School selection (existing or new)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="school_signups",
        verbose_name="Skole",
        help_text="Eksisterende skole fra listen",
    )
    new_school_name = models.CharField(
        max_length=255, blank=True, verbose_name="Nyt skolenavn", help_text="Hvis skolen ikke er på listen"
    )
    municipality = models.CharField(max_length=100, verbose_name="Kommune")

    # Contact person
    contact_name = models.CharField(max_length=255, verbose_name="Kontaktperson")
    contact_email = models.EmailField(verbose_name="E-mail")
    contact_phone = models.CharField(max_length=50, blank=True, verbose_name="Telefon")
    contact_title = models.CharField(max_length=255, blank=True, verbose_name="Stilling")

    # Additional info
    comments = models.TextField(blank=True, verbose_name="Kommentarer")

    # Processing
    created_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False, verbose_name="Behandlet")
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name="Behandlet dato")
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_school_signups",
        verbose_name="Behandlet af",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Skoletilmelding"
        verbose_name_plural = "Skoletilmeldinger"

    def __str__(self):
        school_name = self.school.name if self.school else self.new_school_name
        return f"{school_name} ({self.created_at.strftime('%Y-%m-%d')})"

    @property
    def school_display_name(self):
        """Return the school name, whether existing or new."""
        if self.school:
            return self.school.name
        return self.new_school_name or "Ukendt"
