from datetime import date

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field, Submit
from django import forms

from apps.schools.models import School

from .models import ContactTime


class ContactTimeForm(forms.ModelForm):
    class Meta:
        model = ContactTime
        fields = ['school', 'contacted_date', 'contacted_time', 'inbound', 'comment']
        widgets = {
            'contacted_date': forms.DateInput(attrs={'type': 'date'}),
            'contacted_time': forms.TimeInput(attrs={'type': 'time'}),
            'comment': forms.Textarea(attrs={'rows': 4}),
        }
        labels = {
            'contacted_date': 'Dato',
            'contacted_time': 'Tidspunkt (valgfrit)',
            'inbound': 'Kontaktede de os?',
            'comment': 'Kommentar',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['school'].queryset = School.objects.active()
        self.fields['contacted_time'].required = False

        # Set default date to today for new instances
        if not self.instance.pk:
            self.fields['contacted_date'].initial = date.today()

        self.helper = FormHelper()
        self.helper.layout = Layout(
            'school',
            Row(
                Column('contacted_date', css_class='col-md-6'),
                Column('contacted_time', css_class='col-md-6'),
            ),
            'inbound',
            'comment',
            Submit('submit', 'Gem henvendelse', css_class='btn btn-primary'),
        )
