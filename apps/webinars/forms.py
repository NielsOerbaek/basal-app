from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Field, Layout, Submit
from django import forms

from apps.signups.forms import DynamicFieldsMixin


class _BaseWebinarSignupForm(DynamicFieldsMixin, forms.Form):
    """Common participant fields for both webinar signup variants."""

    name = forms.CharField(max_length=255, label="Navn")
    email = forms.EmailField(label="E-mail")
    phone = forms.CharField(max_length=50, required=False, label="Telefon")
    title = forms.CharField(max_length=255, required=False, label="Titel")

    def __init__(self, *args, signup_page=None, submit_label="Tilmeld", **kwargs):
        super().__init__(*args, **kwargs)
        layout_items = self._participant_layout_items()
        if signup_page:
            self.add_dynamic_fields(signup_page)
            if self.dynamic_fields:
                layout_items.append(HTML("<hr>"))
                layout_items.extend(self.get_dynamic_field_layout())
        layout_items.append(Submit("submit", submit_label, css_class="btn btn-primary btn-lg"))
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(*layout_items)

    def _participant_layout_items(self):
        """Subclasses return the participant-field layout items."""
        raise NotImplementedError


class PublicWebinarSignupForm(_BaseWebinarSignupForm):
    organization = forms.CharField(
        max_length=255,
        required=False,
        label="Organisation",
        help_text="Hvor arbejder du? (valgfrit)",
    )

    def _participant_layout_items(self):
        return [Field("name"), Field("email"), Field("phone"), Field("title"), Field("organization")]


class GatedWebinarSignupForm(_BaseWebinarSignupForm):
    def _participant_layout_items(self):
        return [Field("name"), Field("email"), Field("phone"), Field("title")]
