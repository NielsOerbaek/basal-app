from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, Field, HTML
from django import forms

from .models import School, SeatPurchase, Person, SchoolComment, PersonRole, Invoice


class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ['name', 'adresse', 'kommune', 'enrolled_at']
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
            Row(
                Column('adresse', css_class='col-md-8'),
                Column('kommune', css_class='col-md-4'),
            ),
            'enrolled_at',
            Submit('submit', 'Gem skole', css_class='btn btn-primary'),
        )


class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = ['name', 'role', 'role_other', 'phone', 'email', 'comment', 'is_primary']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'name',
            Row(
                Column('role', css_class='col-md-6'),
                Column('role_other', css_class='col-md-6'),
            ),
            Row(
                Column('phone', css_class='col-md-6'),
                Column('email', css_class='col-md-6'),
            ),
            'comment',
            'is_primary',
            Submit('submit', 'Gem person', css_class='btn btn-primary'),
        )


class SchoolCommentForm(forms.ModelForm):
    class Meta:
        model = SchoolComment
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'comment',
            Submit('submit', 'Gem kommentar', css_class='btn btn-primary'),
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


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['invoice_number', 'amount', 'date', 'status', 'comment']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'comment': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('invoice_number', css_class='col-md-6'),
                Column('amount', css_class='col-md-6'),
            ),
            Row(
                Column('date', css_class='col-md-6'),
                Column('status', css_class='col-md-6'),
            ),
            'comment',
            Submit('submit', 'Gem faktura', css_class='btn btn-primary'),
        )
