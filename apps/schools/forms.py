from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, Field, HTML
from django import forms

from .models import School, SeatPurchase


class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ['name', 'location', 'contact_name', 'contact_email', 'contact_phone', 'enrolled_at', 'comments']
        widgets = {
            'enrolled_at': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'enrolled_at': 'Tilmeldt Basal',
        }

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
            Row(
                Column('contact_phone', css_class='col-md-6'),
                Column('enrolled_at', css_class='col-md-6'),
            ),
            'comments',
            Submit('submit', 'Gem skole', css_class='btn btn-primary'),
        )


class SeatPurchaseForm(forms.ModelForm):
    class Meta:
        model = SeatPurchase
        fields = ['seats', 'purchased_at', 'notes']
        widgets = {
            'purchased_at': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('seats', css_class='col-md-4'),
                Column('purchased_at', css_class='col-md-4'),
            ),
            'notes',
            Submit('submit', 'Tilføj pladser', css_class='btn btn-primary'),
        )
