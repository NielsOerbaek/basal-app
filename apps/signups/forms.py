from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Column, Div, Field, Layout, Row, Submit
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.safestring import mark_safe

from apps.courses.models import Course
from apps.schools.models import School

from .models import FieldType


class DynamicFieldsMixin:
    """
    Mixin that adds dynamic form fields from SignupFormField configuration.
    The form using this mixin must set self.signup_page before calling add_dynamic_fields().
    """

    def add_dynamic_fields(self, signup_page):
        """Add dynamic fields configured for this signup page."""
        self.signup_page = signup_page
        self.dynamic_fields = []

        for field_config in signup_page.form_fields.all():
            field_name = field_config.field_name

            if field_config.field_type == FieldType.CHECKBOX:
                self.fields[field_name] = forms.BooleanField(
                    required=field_config.is_required,
                    label=mark_safe(field_config.label),
                    help_text=field_config.help_text,
                )
            elif field_config.field_type == FieldType.FILE_UPLOAD:
                self.fields[field_name] = forms.FileField(
                    required=field_config.is_required,
                    label=field_config.label,
                    help_text=field_config.help_text or f"Tilladte filtyper: {field_config.allowed_extensions}",
                )

            self.dynamic_fields.append(
                {
                    "name": field_name,
                    "config": field_config,
                }
            )

    def clean_dynamic_fields(self):
        """Validate dynamic file fields."""
        for field_info in getattr(self, "dynamic_fields", []):
            field_config = field_info["config"]
            field_name = field_info["name"]

            if field_config.field_type == FieldType.FILE_UPLOAD:
                uploaded_file = self.cleaned_data.get(field_name)
                if uploaded_file:
                    # Validate file extension
                    allowed_exts = [ext.strip().lower() for ext in field_config.allowed_extensions.split(",")]
                    file_ext = uploaded_file.name.split(".")[-1].lower() if "." in uploaded_file.name else ""
                    if file_ext not in allowed_exts:
                        raise ValidationError(
                            {
                                field_name: f"Filtypen '.{file_ext}' er ikke tilladt. Tilladte typer: {field_config.allowed_extensions}"
                            }
                        )

                    # Validate file size
                    max_size = field_config.max_file_size_mb * 1024 * 1024
                    if uploaded_file.size > max_size:
                        raise ValidationError(
                            {field_name: f"Filen er for stor. Maksimum er {field_config.max_file_size_mb} MB."}
                        )

        return self.cleaned_data

    def get_dynamic_field_layout(self):
        """Return layout items for dynamic fields."""
        items = []
        for field_info in getattr(self, "dynamic_fields", []):
            items.append(Field(field_info["name"]))
        return items


class SchoolChoiceField(forms.ModelChoiceField):
    """Custom field to display school name with kommune."""

    def label_from_instance(self, obj):
        return f"{obj.name} ({obj.kommune})"


class CourseSignupForm(DynamicFieldsMixin, forms.Form):
    """Public course signup form with dynamic fields support."""

    course = forms.ModelChoiceField(
        queryset=Course.objects.none(), label="Vælg et kursus", empty_label="Vælg et kursus..."
    )
    school = SchoolChoiceField(queryset=School.objects.none(), label="Vælg din skole", empty_label="Vælg en skole...")
    participant_name = forms.CharField(max_length=255, label="Navn")
    participant_email = forms.EmailField(label="E-mail")
    participant_title = forms.CharField(max_length=255, required=False, label="Stilling")

    def __init__(self, *args, signup_page=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Set querysets
        self.fields["course"].queryset = Course.objects.filter(
            is_published=True, start_date__gte=timezone.now().date()
        ).order_by("start_date")
        self.fields["school"].queryset = (
            School.objects.active().filter(enrolled_at__isnull=False, opted_out_at__isnull=True).order_by("name")
        )

        # Add dynamic fields if signup_page is provided
        if signup_page:
            self.add_dynamic_fields(signup_page)

        # Build layout
        submit_text = signup_page.submit_button_text if signup_page else "Tilmeld"
        layout_items = [
            "course",
            "school",
            HTML("<hr><h5>Deltagerinformation</h5>"),
            "participant_name",
            Row(
                Column("participant_email", css_class="col-md-6"),
                Column("participant_title", css_class="col-md-6"),
            ),
        ]

        # Add dynamic fields to layout
        if hasattr(self, "dynamic_fields") and self.dynamic_fields:
            layout_items.append(HTML("<hr><h5>Yderligere oplysninger</h5>"))
            layout_items.extend(self.get_dynamic_field_layout())

        layout_items.append(Submit("submit", submit_text, css_class="btn btn-primary btn-lg"))

        self.helper = FormHelper()
        self.helper.layout = Layout(*layout_items)

    def clean(self):
        cleaned_data = super().clean()
        # Validate dynamic fields
        self.clean_dynamic_fields()
        return cleaned_data


class SchoolSignupForm(DynamicFieldsMixin, forms.Form):
    """School signup form for joining the Basal project."""

    municipality = forms.ChoiceField(
        label="Kommune",
        choices=[("", "Vælg kommune...")],
    )
    school = SchoolChoiceField(
        queryset=School.objects.none(),
        label="Vælg skole",
        empty_label="Vælg en skole...",
        required=False,
    )
    school_not_listed = forms.BooleanField(
        required=False,
        label="Min skole er ikke på listen",
    )
    new_school_name = forms.CharField(
        max_length=255,
        required=False,
        label="Skolens navn",
    )

    contact_name = forms.CharField(max_length=255, label="Dit navn")
    contact_email = forms.EmailField(label="E-mail")
    contact_phone = forms.CharField(max_length=50, required=False, label="Telefon")
    contact_title = forms.CharField(max_length=255, required=False, label="Din stilling")

    comments = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Kommentarer",
        help_text="Eventuelle spørgsmål eller bemærkninger",
    )

    def __init__(self, *args, signup_page=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Get unique municipalities from active schools
        municipalities = School.objects.active().values_list("kommune", flat=True).distinct().order_by("kommune")
        self.fields["municipality"].choices = [("", "Vælg kommune...")] + [(m, m) for m in municipalities]

        # If form is bound (POST), populate school queryset based on municipality
        if self.is_bound:
            municipality = self.data.get("municipality", "")
            if municipality:
                self.fields["school"].queryset = (
                    School.objects.active().filter(kommune__iexact=municipality).order_by("name")
                )

        # Add dynamic fields if signup_page is provided
        if signup_page:
            self.add_dynamic_fields(signup_page)

        # Build layout
        submit_text = signup_page.submit_button_text if signup_page else "Send tilmelding"
        layout_items = [
            HTML("<h5>Skoleoplysninger</h5>"),
            "municipality",
            Div("school", "school_not_listed", css_id="school-selection"),
            Div("new_school_name", css_id="new-school-fields", style="display: none;"),
            HTML("<hr><h5>Kontaktoplysninger</h5>"),
            "contact_name",
            Row(
                Column("contact_email", css_class="col-md-6"),
                Column("contact_phone", css_class="col-md-6"),
            ),
            "contact_title",
            "comments",
        ]

        # Add dynamic fields to layout
        if hasattr(self, "dynamic_fields") and self.dynamic_fields:
            layout_items.append(HTML("<hr><h5>Yderligere oplysninger</h5>"))
            layout_items.extend(self.get_dynamic_field_layout())

        layout_items.append(Submit("submit", submit_text, css_class="btn btn-primary btn-lg"))

        self.helper = FormHelper()
        self.helper.layout = Layout(*layout_items)

    def clean(self):
        cleaned_data = super().clean()
        school_not_listed = cleaned_data.get("school_not_listed")
        school = cleaned_data.get("school")
        new_school_name = cleaned_data.get("new_school_name")

        if school_not_listed:
            if not new_school_name:
                raise ValidationError({"new_school_name": "Angiv venligst skolens navn."})
        else:
            if not school:
                raise ValidationError({"school": "Vælg venligst en skole eller marker at din skole ikke er på listen."})

        # Validate dynamic fields
        self.clean_dynamic_fields()
        return cleaned_data
