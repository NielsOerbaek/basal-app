from datetime import date

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Div, Field, Layout, Row, Submit
from django import forms

from apps.schools.models import Person, School

from .models import ContactTime


class ContactTimeForm(forms.ModelForm):
    contacted_persons = forms.ModelMultipleChoiceField(
        queryset=Person.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Hvem talte du med?",
    )
    contacted_other = forms.BooleanField(
        required=False,
        label="Anden (ikke på listen)",
    )

    class Meta:
        model = ContactTime
        fields = [
            "school",
            "contacted_date",
            "contacted_time",
            "contacted_persons",
            "contacted_other",
            "inbound",
            "comment",
        ]
        widgets = {
            "contacted_date": forms.DateInput(attrs={"type": "date"}),
            "contacted_time": forms.TimeInput(attrs={"type": "time"}),
            "comment": forms.Textarea(attrs={"rows": 4}),
        }
        labels = {
            "contacted_date": "Dato",
            "contacted_time": "Tidspunkt (valgfrit)",
            "inbound": "Kontaktede de os?",
            "comment": "Kommentar",
        }

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["school"].queryset = School.objects.active()
        self.fields["contacted_time"].required = False

        # Set default date to today for new instances
        if not self.instance.pk:
            self.fields["contacted_date"].initial = date.today()

        # Set up persons queryset based on school
        if school:
            self.fields["contacted_persons"].queryset = school.people.all()
        elif self.instance.pk and self.instance.school:
            self.fields["contacted_persons"].queryset = self.instance.school.people.all()

        self.helper = FormHelper()
        self.helper.layout = Layout(
            "school",
            Row(
                Column("contacted_date", css_class="col-md-6"),
                Column(
                    Field("contacted_time", wrapper_class="time-field-wrapper"),
                    css_class="col-md-6",
                ),
            ),
            "inbound",
            Div(
                Field("contacted_persons", wrapper_class="mb-2"),
                "contacted_other",
                css_id="persons-section",
            ),
            "comment",
            Submit("submit", "Gem henvendelse", css_class="btn btn-primary"),
        )
