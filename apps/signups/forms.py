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
        # Format date
        if obj.start_date == obj.end_date:
            date_str = obj.start_date.strftime("%-d. %b %Y")
        else:
            date_str = f"{obj.start_date.strftime('%-d. %b')} - {obj.end_date.strftime('%-d. %b %Y')}"

        # Format available seats
        available = obj.spots_remaining
        if available <= 0:
            seats_text = "Fuldt"
        elif available == 1:
            seats_text = "1 ledig plads"
        else:
            seats_text = f"{available} ledige pladser"

        return f"{obj.title} - {date_str} - {seats_text}"


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
                            <dd id="course-location" class="mb-0">-</dd>
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
    new_school_address = forms.CharField(
        max_length=255,
        required=False,
        label="Skolens adresse",
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
            Div("new_school_name", "new_school_address", css_id="new-school-fields", style="display: none;"),
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
            layout_items.append(HTML("<hr>"))
            layout_items.extend(self.get_dynamic_field_layout())

        layout_items.append(Submit("submit", submit_text, css_class="btn btn-primary btn-lg"))

        self.helper = FormHelper()
        self.helper.layout = Layout(*layout_items)

    def clean(self):
        cleaned_data = super().clean()
        school_not_listed = cleaned_data.get("school_not_listed")
        school = cleaned_data.get("school")
        new_school_name = cleaned_data.get("new_school_name")
        new_school_address = cleaned_data.get("new_school_address")

        if school_not_listed:
            if not new_school_name:
                raise ValidationError({"new_school_name": "Angiv venligst skolens navn."})
            if not new_school_address:
                raise ValidationError({"new_school_address": "Angiv venligst skolens adresse."})
        else:
            if not school:
                raise ValidationError({"school": "Vælg venligst en skole eller marker at din skole ikke er på listen."})

        return cleaned_data
