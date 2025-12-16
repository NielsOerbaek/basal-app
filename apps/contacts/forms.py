from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit
from django import forms

from apps.schools.models import School

from .models import ContactTime


class ContactTimeForm(forms.ModelForm):
    class Meta:
        model = ContactTime
        fields = ['school', 'contacted_at', 'comment']
        widgets = {
            'contacted_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'comment': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['school'].queryset = School.objects.active()
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'school',
            'contacted_at',
            'comment',
            Submit('submit', 'Gem henvendelse', css_class='btn btn-primary'),
        )
