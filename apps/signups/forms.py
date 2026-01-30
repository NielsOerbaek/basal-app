from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Column, Div, Field, Layout, Row, Submit
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.safestring import mark_safe

from apps.courses.models import Course
from apps.courses.utils import format_date_danish
from apps.schools.models import School, TitelChoice

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
                # Build label with download link if attachment exists
                label = field_config.label
                if field_config.attachment:
                    label += f' <a href="{field_config.attachment.url}" target="_blank" class="text-decoration-underline">(Download dokument)</a>'

                self.fields[field_name] = forms.BooleanField(
                    required=field_config.is_required,
                    label=mark_safe(label),
                    help_text=field_config.help_text,
                )

            self.dynamic_fields.append(
                {
                    "name": field_name,
                    "config": field_config,
                }
            )

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


class CourseChoiceField(forms.ModelChoiceField):
    """Custom field to display course with available seats."""

    def label_from_instance(self, obj):
        # Format date in Danish locale
        if obj.start_date == obj.end_date:
            date_str = format_date_danish(obj.start_date)
        else:
            date_str = f"{format_date_danish(obj.start_date, include_year=False)} - {format_date_danish(obj.end_date)}"

        # Format available seats
        available = obj.spots_remaining
        if available <= 0:
            seats_text = "Fuldt"
        elif available == 1:
            seats_text = "1 ledig plads"
        else:
            seats_text = f"{available} ledige pladser"

        return f"{obj.display_name} - {date_str} - {seats_text}"


class CourseSignupForm(DynamicFieldsMixin, forms.Form):
    """Public course signup form with dynamic fields support.

    Note: Participant fields are rendered manually in the template to allow
    adding multiple participants dynamically with JavaScript.
    """

    course = CourseChoiceField(queryset=Course.objects.none(), label="Vælg et kursus", empty_label="Vælg et kursus...")
    school = SchoolChoiceField(queryset=School.objects.none(), label="Vælg din skole", empty_label="Vælg en skole...")

    def __init__(self, *args, signup_page=None, locked_school=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.locked_school = locked_school

        # Set querysets
        self.fields["course"].queryset = Course.objects.filter(
            is_published=True, start_date__gte=timezone.now().date()
        ).order_by("start_date")

        if locked_school:
            # Lock to specific school
            self.fields["school"].queryset = School.objects.filter(pk=locked_school.pk)
            self.fields["school"].initial = locked_school
            self.fields["school"].empty_label = None
            self.fields["school"].widget.attrs["disabled"] = True
        else:
            self.fields["school"].queryset = (
                School.objects.active().filter(enrolled_at__isnull=False, opted_out_at__isnull=True).order_by("name")
            )

        # Add dynamic fields if signup_page is provided
        if signup_page:
            self.add_dynamic_fields(signup_page)

        # Build layout - participant fields are rendered manually in template
        # Course details card is inserted after course dropdown (populated via JS)
        course_details_html = """
        <div id="course-details" class="card mb-3" style="display: none;">
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <dl class="mb-0">
                            <dt><i class="bi bi-calendar-event me-1"></i>Dato</dt>
                            <dd id="course-date" class="mb-2">-</dd>
                            <dt><i class="bi bi-geo-alt me-1"></i>Sted</dt>
                            <dd id="course-location" class="mb-2">-</dd>
                            <dt><i class="bi bi-clock me-1"></i>Tilmeldingsfrist</dt>
                            <dd id="course-deadline" class="mb-0">-</dd>
                        </dl>
                    </div>
                    <div class="col-md-6">
                        <dl class="mb-0">
                            <dt><i class="bi bi-person me-1"></i>Undervisere</dt>
                            <dd id="course-undervisere" class="mb-2">-</dd>
                            <dt><i class="bi bi-people me-1"></i>Ledige pladser</dt>
                            <dd id="course-available-seats" class="mb-0">-</dd>
                        </dl>
                    </div>
                </div>
            </div>
        </div>
        <div id="course-full-warning" class="alert alert-danger" style="display: none;">
            <strong><i class="bi bi-x-circle me-2"></i>Kurset er fuldt</strong>
            <span id="course-full-text"></span>
        </div>
        """
        layout_items = [
            "course",
            HTML(course_details_html),
            "school",
        ]

        # Add dynamic fields to layout
        if hasattr(self, "dynamic_fields") and self.dynamic_fields:
            layout_items.append(HTML("<hr>"))
            layout_items.extend(self.get_dynamic_field_layout())

        self.helper = FormHelper()
        self.helper.form_tag = False  # We'll handle form tag in template
        self.helper.layout = Layout(*layout_items)

    def clean_school(self):
        """Handle locked school - disabled fields don't submit values."""
        if self.locked_school:
            return self.locked_school
        return self.cleaned_data.get("school")


class SchoolSignupForm(DynamicFieldsMixin, forms.Form):
    """School signup form for joining the Basal project."""

    # School selection
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

    # New school fields (only shown when school_not_listed)
    new_school_name = forms.CharField(max_length=255, required=False, label="Skolens navn")
    new_school_address = forms.CharField(max_length=255, required=False, label="Adresse")
    new_school_postnummer = forms.CharField(max_length=4, required=False, label="Postnummer")
    new_school_by = forms.CharField(max_length=100, required=False, label="By")

    # School EAN (required for all)
    ean_nummer = forms.CharField(max_length=13, label="EAN-nummer", help_text="13-cifret EAN-nummer til fakturering")

    # Koordinator - contact to Komiteen for Sundhedsoplysning
    koordinator_name = forms.CharField(max_length=255, label="Navn")
    koordinator_titel = forms.ChoiceField(label="Titel", choices=[])  # Will be set in __init__
    koordinator_titel_other = forms.CharField(max_length=100, required=False, label="Anden titel")
    koordinator_phone = forms.CharField(max_length=50, label="Telefon")
    koordinator_email = forms.EmailField(label="E-mail")

    # Økonomisk ansvarlig
    oeko_name = forms.CharField(max_length=255, label="Navn")
    oeko_titel = forms.ChoiceField(label="Titel", choices=[])  # Will be set in __init__
    oeko_titel_other = forms.CharField(max_length=100, required=False, label="Anden titel")
    oeko_phone = forms.CharField(max_length=50, label="Telefon")
    oeko_email = forms.EmailField(label="E-mail")

    # Billing fields (when municipality pays)
    kommunen_betaler = forms.BooleanField(required=False, label="Kommunen betaler (anden faktureringsadresse)")
    fakturering_adresse = forms.CharField(max_length=255, required=False, label="Faktureringsadresse")
    fakturering_postnummer = forms.CharField(max_length=4, required=False, label="Postnummer")
    fakturering_by = forms.CharField(max_length=100, required=False, label="By")
    fakturering_ean_nummer = forms.CharField(max_length=13, required=False, label="EAN-nummer")
    fakturering_kontakt_navn = forms.CharField(max_length=255, required=False, label="Kontaktperson")
    fakturering_kontakt_email = forms.EmailField(required=False, label="E-mail")

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

        # Add empty choice and set choices for titel fields
        titel_choices = [("", "Vælg titel...")] + list(TitelChoice.choices)
        self.fields["koordinator_titel"].choices = titel_choices
        self.fields["oeko_titel"].choices = titel_choices

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
            Div(
                "new_school_name",
                "new_school_address",
                Row(
                    Column("new_school_postnummer", css_class="col-md-4"),
                    Column("new_school_by", css_class="col-md-8"),
                ),
                css_id="new-school-fields",
                style="display: none;",
            ),
            "ean_nummer",
            HTML("<hr><h5>Koordinator - kontaktperson til Komiteen for Sundhedsoplysning</h5>"),
            Row(
                Column("koordinator_name", css_class="col-md-6"),
                Column("koordinator_titel", css_class="col-md-3"),
                Column("koordinator_titel_other", css_class="col-md-3"),
            ),
            Row(
                Column("koordinator_email", css_class="col-md-6"),
                Column("koordinator_phone", css_class="col-md-6"),
            ),
            HTML("<hr><h5>Økonomisk ansvarlig</h5>"),
            Row(
                Column("oeko_name", css_class="col-md-6"),
                Column("oeko_titel", css_class="col-md-3"),
                Column("oeko_titel_other", css_class="col-md-3"),
            ),
            Row(
                Column("oeko_email", css_class="col-md-6"),
                Column("oeko_phone", css_class="col-md-6"),
            ),
            HTML("<hr><h5>Fakturering</h5>"),
            "kommunen_betaler",
            Div(
                "fakturering_adresse",
                Row(
                    Column("fakturering_postnummer", css_class="col-md-4"),
                    Column("fakturering_by", css_class="col-md-8"),
                ),
                "fakturering_ean_nummer",
                Row(
                    Column("fakturering_kontakt_navn", css_class="col-md-6"),
                    Column("fakturering_kontakt_email", css_class="col-md-6"),
                ),
                css_id="billing-fields",
                style="display: none;",
            ),
            "comments",
        ]

        # Add dynamic fields to layout
        if hasattr(self, "dynamic_fields") and self.dynamic_fields:
            layout_items.append(HTML("<hr>"))
            layout_items.extend(self.get_dynamic_field_layout())

        layout_items.append(Submit("submit", submit_text, css_class="btn btn-primary btn-lg"))

        self.helper = FormHelper()
        self.helper.layout = Layout(*layout_items)

    def clean(self):
        cleaned_data = super().clean()
        school_not_listed = cleaned_data.get("school_not_listed")
        school = cleaned_data.get("school")
        kommunen_betaler = cleaned_data.get("kommunen_betaler")

        if school_not_listed:
            if not cleaned_data.get("new_school_name"):
                raise ValidationError({"new_school_name": "Angiv venligst skolens navn."})
            if not cleaned_data.get("new_school_address"):
                raise ValidationError({"new_school_address": "Angiv venligst skolens adresse."})
            if not cleaned_data.get("new_school_postnummer"):
                raise ValidationError({"new_school_postnummer": "Angiv venligst postnummer."})
            if not cleaned_data.get("new_school_by"):
                raise ValidationError({"new_school_by": "Angiv venligst by."})
        else:
            if not school:
                raise ValidationError({"school": "Vælg venligst en skole eller marker at din skole ikke er på listen."})

        if kommunen_betaler:
            if not cleaned_data.get("fakturering_adresse"):
                raise ValidationError({"fakturering_adresse": "Angiv venligst faktureringsadresse."})
            if not cleaned_data.get("fakturering_ean_nummer"):
                raise ValidationError({"fakturering_ean_nummer": "Angiv venligst EAN-nummer for fakturering."})

        return cleaned_data
