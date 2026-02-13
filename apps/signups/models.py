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
    label = models.CharField(max_length=500, verbose_name="Label", help_text="Feltnavn/tekst (HTML tilladt)")
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


class SeatInfoScenario(models.TextChoices):
    FIRST_YEAR_UNUSED = "first_year_unused", "Første år – ubrugte pladser"
    FIRST_YEAR_ALL_USED = "first_year_all_used", "Første år – alle pladser brugt"
    FIRST_YEAR_EXTRA = "first_year_extra", "Første år – ekstra pladser"
    FORTSAETTER_AVAILABLE = "fortsaetter_available", "Fortsætter – plads tilgængelig"
    FORTSAETTER_NONE = "fortsaetter_none", "Fortsætter – ingen gratis pladser"


class SeatInfoContent(models.Model):
    """Admin-editable content for seat info boxes on course signup page."""

    scenario = models.CharField(
        max_length=30,
        unique=True,
        choices=SeatInfoScenario.choices,
        verbose_name="Scenarie",
    )
    title = models.CharField(max_length=255, verbose_name="Overskrift")
    content = models.TextField(
        verbose_name="Indhold",
        help_text="HTML-tekst der vises i informationsboksen",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pladsinformation"
        verbose_name_plural = "Pladsinformationer"
        ordering = ["scenario"]

    def __str__(self):
        return self.get_scenario_display()
