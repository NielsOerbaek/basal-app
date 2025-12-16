from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit
from django import forms

from .models import School


class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ['name', 'location', 'contact_name', 'contact_email', 'contact_phone', 'comments']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'name',
            'location',
            Row(
                Column('contact_name', css_class='col-md-6'),
                Column('contact_email', css_class='col-md-6'),
            ),
            'contact_phone',
            'comments',
            Submit('submit', 'Gem skole', css_class='btn btn-primary'),
        )
