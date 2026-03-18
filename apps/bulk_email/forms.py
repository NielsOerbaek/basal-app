from django import forms
from django_summernote.widgets import SummernoteWidget

from apps.bulk_email.models import BulkEmail


class BulkEmailComposeForm(forms.Form):
    subject = forms.CharField(
        max_length=500,
        label="Emne",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Emne — brug {{ variabel }} for dynamisk indhold",
            }
        ),
    )
    body_html = forms.CharField(
        label="Indhold",
        widget=SummernoteWidget(),
        required=False,
    )
    recipient_type = forms.ChoiceField(
        choices=BulkEmail.RECIPIENT_TYPE_CHOICES,
        label="Modtagertype",
        widget=forms.RadioSelect(),
        initial=BulkEmail.KOORDINATOR,
    )
