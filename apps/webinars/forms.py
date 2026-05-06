from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Field, Layout, Submit
from django import forms

from apps.schools.models import Kommune
from apps.signups.forms import DynamicFieldsMixin


class WebinarSignupForm(DynamicFieldsMixin, forms.Form):
    """Public webinar signup form. Anyone can submit — no school auth."""

    kommune = forms.ModelChoiceField(
        queryset=Kommune.objects.order_by("name"),
        label="Kommune",
        empty_label="Vælg kommune...",
    )
    school_name = forms.CharField(max_length=255, label="Skole")
    name = forms.CharField(max_length=255, label="Navn")
    email = forms.EmailField(label="E-mail")

    def __init__(self, *args, signup_page=None, submit_label="Tilmeld", **kwargs):
        super().__init__(*args, **kwargs)
        layout_items = [
            Field("kommune"),
            Field("school_name"),
            Field("name"),
            Field("email"),
        ]
        if signup_page:
            self.add_dynamic_fields(signup_page)
            if self.dynamic_fields:
                layout_items.append(HTML("<hr>"))
                layout_items.extend(self.get_dynamic_field_layout())
        layout_items.append(Submit("submit", submit_label, css_class="btn btn-primary btn-lg"))
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(*layout_items)
