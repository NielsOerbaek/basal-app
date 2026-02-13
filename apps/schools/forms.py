from datetime import date

from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Column, Div, Layout, Row, Submit
from django import forms

from .constants import DANISH_KOMMUNER
from .models import Invoice, Person, School, SchoolComment, SchoolFile
from .school_years import (
    calculate_school_year_for_date,
    format_school_year,
    get_school_year_dates,
    parse_school_year,
)


class SchoolForm(forms.ModelForm):
    kommune = forms.ChoiceField(
        choices=[("", "---------")] + list(DANISH_KOMMUNER),
        label="Kommune",
    )

    class Meta:
        model = School
        fields = [
            "name",
            "adresse",
            "postnummer",
            "by",
            "kommune",
            "ean_nummer",
            "kommunen_betaler",
            "fakturering_adresse",
            "fakturering_postnummer",
            "fakturering_by",
            "fakturering_ean_nummer",
            "fakturering_kontakt_navn",
            "fakturering_kontakt_email",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["adresse"].required = False
        self.fields["postnummer"].required = False
        self.fields["by"].required = False
        self.fields["ean_nummer"].required = False
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            "name",
            Row(
                Column("adresse", css_class="col-md-6"),
                Column("postnummer", css_class="col-md-2"),
                Column("by", css_class="col-md-4"),
            ),
            Row(
                Column("kommune", css_class="col-md-6"),
                Column("ean_nummer", css_class="col-md-6"),
            ),
            HTML("<hr><h5>Fakturering</h5>"),
            "kommunen_betaler",
            Div(
                Row(
                    Column("fakturering_adresse", css_class="col-md-6"),
                    Column("fakturering_postnummer", css_class="col-md-2"),
                    Column("fakturering_by", css_class="col-md-4"),
                ),
                Row(
                    Column("fakturering_ean_nummer", css_class="col-md-4"),
                    Column("fakturering_kontakt_navn", css_class="col-md-4"),
                    Column("fakturering_kontakt_email", css_class="col-md-4"),
                ),
                css_id="billing-fields",
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        kommune = cleaned_data.get("kommune")

        if name and kommune:
            # Check for duplicate school (exclude current instance if editing)
            qs = School.objects.filter(name=name, kommune=kommune)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(f'Der findes allerede en skole med navnet "{name}" i {kommune}.')

        return cleaned_data


class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = [
            "name",
            "titel",
            "titel_other",
            "phone",
            "email",
            "comment",
            "is_koordinator",
            "is_oekonomisk_ansvarlig",
        ]
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column("name", css_class="col-md-6"),
                Column("titel", css_class="col-md-3"),
                Column("titel_other", css_class="col-md-3"),
            ),
            Row(
                Column("phone", css_class="col-md-6"),
                Column("email", css_class="col-md-6"),
            ),
            "comment",
            Row(
                Column("is_koordinator", css_class="col-md-6"),
                Column("is_oekonomisk_ansvarlig", css_class="col-md-6"),
            ),
        )


class SchoolCommentForm(forms.ModelForm):
    class Meta:
        model = SchoolComment
        fields = ["comment"]
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "comment",
            Submit("submit", "Gem kommentar", css_class="btn btn-primary"),
        )


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["school_year", "invoice_number", "amount", "date", "status", "comment"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "comment": forms.Textarea(attrs={"rows": 2}),
            "school_year": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, school=None, initial_school_year=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.school = school
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "school_year",
            Row(
                Column("invoice_number", css_class="col-md-6"),
                Column("amount", css_class="col-md-6"),
            ),
            Row(
                Column("date", css_class="col-md-6"),
                Column("status", css_class="col-md-6"),
            ),
            "comment",
            Submit("submit", "Gem faktura", css_class="btn btn-primary"),
        )
        # Limit school_year choices to years the school is enrolled in, up to next year
        if school:
            from .models import SchoolYear

            # Get current school year to determine cutoff
            current_year = SchoolYear.objects.get_current()
            enrolled_years = school.get_enrolled_years().order_by("-start_date")

            if current_year:
                # Only show up to 1 year after current (the "next" year)
                next_year_end = current_year.end_date.replace(year=current_year.end_date.year + 1)
                enrolled_years = enrolled_years.filter(start_date__lte=next_year_end)

            self.fields["school_year"].queryset = enrolled_years

        # Set initial school_year if provided
        if initial_school_year:
            self.fields["school_year"].initial = initial_school_year

    def clean(self):
        cleaned_data = super().clean()
        invoice_number = cleaned_data.get("invoice_number")
        school_year = cleaned_data.get("school_year")

        if invoice_number and school_year:
            # Check for duplicate invoice_number + school_year (exclude current instance if editing)
            qs = Invoice.objects.filter(invoice_number=invoice_number, school_year=school_year)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f'Der findes allerede en faktura med nummer "{invoice_number}" for skoleåret {school_year.name}.'
                )

        return cleaned_data


class SchoolFileForm(forms.ModelForm):
    class Meta:
        model = SchoolFile
        fields = ["file", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        editing = self.instance and self.instance.pk
        if editing:
            self.fields["file"].required = False
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "file",
            "description",
            Submit("submit", "Gem ændringer" if editing else "Upload fil", css_class="btn btn-primary"),
        )


class EnrollmentDatesForm(forms.ModelForm):
    active_from_year = forms.ChoiceField(
        label="Aktiv fra (skoleår)",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = School
        fields = ["enrolled_at"]
        widgets = {
            "enrolled_at": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }
        labels = {
            "enrolled_at": "Tilmeldt d.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Determine the base date for generating school year choices
        enrolled_at = None
        if self.instance and self.instance.pk:
            enrolled_at = self.instance.enrolled_at
        if not enrolled_at and self.data:
            raw = self.data.get(self.add_prefix("enrolled_at"))
            if raw:
                try:
                    enrolled_at = date.fromisoformat(raw)
                except (ValueError, TypeError):
                    pass
        base_date = enrolled_at or date.today()

        # Build 5 school year choices starting from the school year of base_date
        base_year_str = calculate_school_year_for_date(base_date)
        base_start_year = parse_school_year(base_year_str)
        choices = []
        for i in range(5):
            yr_str = format_school_year(base_start_year + i)
            choices.append((yr_str, yr_str))

        # Pre-select the school year that active_from falls in (if editing)
        current_active_from_year = None
        if self.instance and self.instance.pk and self.instance.active_from:
            current_active_from_year = calculate_school_year_for_date(self.instance.active_from)
            # If the current year is outside the 5 choices, prepend it
            choice_values = [c[0] for c in choices]
            if current_active_from_year not in choice_values:
                choices.insert(0, (current_active_from_year, current_active_from_year))

        self.fields["active_from_year"].choices = choices

        # Set initial value for the dropdown
        if current_active_from_year:
            self.fields["active_from_year"].initial = current_active_from_year

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column("enrolled_at", css_class="col-md-6"),
                Column("active_from_year", css_class="col-md-6"),
            ),
            HTML(
                '<p class="form-text text-muted small">'
                "<strong>Tilmeldt d.</strong> er datoen skolen tilmeldte sig. "
                "<strong>Aktiv fra (skoleår)</strong> er det skoleår tilmeldingen træder i kraft og bestemmer pladser og fortsætter-status."
                "</p>"
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        enrolled_at = cleaned_data.get("enrolled_at")
        selected_year = cleaned_data.get("active_from_year")

        if enrolled_at and selected_year:
            enrolled_year_str = calculate_school_year_for_date(enrolled_at)
            if selected_year == enrolled_year_str:
                # Same school year as enrolled_at: use enrolled_at as active_from
                active_from = enrolled_at
            else:
                # Different school year: use Aug 1st of that year
                start_date, _ = get_school_year_dates(selected_year)
                active_from = start_date

            if active_from < enrolled_at:
                raise forms.ValidationError("'Aktiv fra' kan ikke være før 'Tilmeldt d.'")

            cleaned_data["active_from"] = active_from

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.active_from = self.cleaned_data["active_from"]
        if commit:
            instance.save()
        return instance
