from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Layout, Row, Submit
from django import forms

from .constants import DANISH_KOMMUNER
from .models import Invoice, Person, School, SchoolComment


class SchoolForm(forms.ModelForm):
    kommune = forms.ChoiceField(
        choices=[("", "---------")] + list(DANISH_KOMMUNER),
        label="Kommune",
    )

    class Meta:
        model = School
        fields = ["name", "adresse", "postnummer", "by", "kommune", "ean_nummer", "enrolled_at", "opted_out_at"]
        widgets = {
            "enrolled_at": forms.DateInput(attrs={"type": "date"}),
            "opted_out_at": forms.DateInput(attrs={"type": "date"}),
        }
        labels = {
            "enrolled_at": "Tilmeldt siden",
            "opted_out_at": "Frameldt dato",
        }
        help_texts = {
            "enrolled_at": "Dato for tilmelding til Basal",
            "opted_out_at": "Udfyld kun hvis skolen har frameldt sig permanent",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["adresse"].required = False
        self.fields["postnummer"].required = False
        self.fields["by"].required = False
        self.fields["ean_nummer"].required = False
        self.helper = FormHelper()
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
            Row(
                Column("enrolled_at", css_class="col-md-6"),
                Column("opted_out_at", css_class="col-md-6"),
            ),
            Submit("submit", "Gem skole", css_class="btn btn-primary"),
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
        fields = ["name", "role", "role_other", "phone", "email", "comment", "is_primary"]
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "name",
            Row(
                Column("role", css_class="col-md-6"),
                Column("role_other", css_class="col-md-6"),
            ),
            Row(
                Column("phone", css_class="col-md-6"),
                Column("email", css_class="col-md-6"),
            ),
            "comment",
            "is_primary",
            Submit("submit", "Gem person", css_class="btn btn-primary"),
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

    def __init__(self, *args, school=None, **kwargs):
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
        # Limit school_year choices to years the school is enrolled in
        if school:
            self.fields["school_year"].queryset = school.get_enrolled_years().order_by("-start_date")

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
