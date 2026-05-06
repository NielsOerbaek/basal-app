from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Column, Div, Field, Layout, Row, Submit
from django import forms
from django_summernote.widgets import SummernoteWidget

from apps.courses.models import Instructor
from apps.schools.models import Kommune
from apps.signups.forms import DynamicFieldsMixin

from .models import Webinar

# ---------------------------------------------------------------------------
# Public signup form
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Admin-facing CRUD form
# ---------------------------------------------------------------------------


class _AddNewModelChoiceField(forms.ModelChoiceField):
    """ModelChoiceField that accepts '__new__' as a special value for adding new items."""

    def to_python(self, value):
        if value == "__new__":
            return value
        return super().to_python(value)

    def validate(self, value):
        if value == "__new__":
            return
        return super().validate(value)


class WebinarForm(forms.ModelForm):
    """Admin-facing create/edit form for a Webinar. Mirrors the look of CourseForm."""

    instructor_1 = _AddNewModelChoiceField(
        queryset=Instructor.objects.all().order_by("name"),
        required=False,
        label="Oplægsholder 1",
        empty_label="Vælg oplægsholder...",
    )
    instructor_2 = _AddNewModelChoiceField(
        queryset=Instructor.objects.all().order_by("name"),
        required=False,
        label="Oplægsholder 2",
        empty_label="Vælg oplægsholder...",
    )
    instructor_3 = _AddNewModelChoiceField(
        queryset=Instructor.objects.all().order_by("name"),
        required=False,
        label="Oplægsholder 3",
        empty_label="Vælg oplægsholder...",
    )
    new_instructor_1 = forms.CharField(required=False, label="Ny oplægsholder 1")
    new_instructor_2 = forms.CharField(required=False, label="Ny oplægsholder 2")
    new_instructor_3 = forms.CharField(required=False, label="Ny oplægsholder 3")

    class Meta:
        model = Webinar
        fields = [
            "title",
            "slug",
            "description",
            "start_at",
            "duration_minutes",
            "meeting_url",
            "capacity",
            "is_published",
        ]
        widgets = {
            "description": SummernoteWidget(),
            "start_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Slug is optional — auto-generated from title if blank, server-side.
        # JS prepopulates it client-side as the user types the title.
        self.fields["slug"].required = False
        self.fields["slug"].help_text = "Auto-udfyldes fra titlen. URL-formatet bliver /webinar/<slug>/."

        # datetime-local widget needs the input_formats hint for parsing
        self.fields["start_at"].input_formats = ["%Y-%m-%dT%H:%M"]

        # Add "+ Tilføj ny oplægsholder" option to instructor choices
        instructor_choices = [("", "Vælg oplægsholder..."), ("__new__", "+ Tilføj ny oplægsholder")]
        instructor_choices.extend([(i.pk, i.name) for i in Instructor.objects.all().order_by("name")])
        self.fields["instructor_1"].choices = instructor_choices
        self.fields["instructor_2"].choices = instructor_choices
        self.fields["instructor_3"].choices = instructor_choices

        # Pre-populate instructor fields when editing
        if self.instance and self.instance.pk:
            instructors = list(self.instance.instructors.all())
            if len(instructors) > 0:
                self.initial["instructor_1"] = instructors[0].pk
            if len(instructors) > 1:
                self.initial["instructor_2"] = instructors[1].pk
            if len(instructors) > 2:
                self.initial["instructor_3"] = instructors[2].pk

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            "title",
            "slug",
            HTML("<h5 class='mt-3'>Beskrivelse</h5>"),
            "description",
            HTML("<h5 class='mt-3'>Tidspunkt</h5>"),
            Row(
                Column("start_at", css_class="col-md-8"),
                Column("duration_minutes", css_class="col-md-4"),
            ),
            HTML("<h5 class='mt-3'>Mødelink</h5>"),
            "meeting_url",
            HTML(
                "<p class='text-muted small mt-1 mb-3'>"
                "<i class='bi bi-info-circle me-1'></i>"
                "Hvis tomt, oplyses deltageren i bekræftelses-mailen om at linket eftersendes tættere på datoen."
                "</p>"
            ),
            HTML("<h5 class='mt-3'>Oplægsholdere</h5>"),
            Row(
                Column(
                    Field("instructor_1"),
                    Div(Field("new_instructor_1"), css_id="new-instructor-1-container", css_class="d-none"),
                    css_class="col-md-4",
                ),
                Column(
                    Field("instructor_2"),
                    Div(Field("new_instructor_2"), css_id="new-instructor-2-container", css_class="d-none"),
                    css_class="col-md-4",
                ),
                Column(
                    Field("instructor_3"),
                    Div(Field("new_instructor_3"), css_id="new-instructor-3-container", css_class="d-none"),
                    css_class="col-md-4",
                ),
            ),
            HTML("<h5 class='mt-3'>Andet</h5>"),
            "capacity",
            "is_published",
        )

    def clean(self):
        cleaned_data = super().clean()

        # Resolve "__new__" instructors → create them now so save() can attach them
        self._created_instructors = []
        for i in range(1, 4):
            instructor_val = self.data.get(f"instructor_{i}")
            new_name = cleaned_data.get(f"new_instructor_{i}")
            if instructor_val == "__new__":
                if not new_name:
                    self.add_error(f"new_instructor_{i}", "Oplægsholdernavn er påkrævet")
                else:
                    instructor, _ = Instructor.objects.get_or_create(name=new_name)
                    cleaned_data[f"instructor_{i}"] = instructor
                    self._created_instructors.append(instructor)

        return cleaned_data

    def save(self, commit=True):
        from django.utils.text import slugify

        instance = super().save(commit=False)

        if not instance.slug and instance.title:
            instance.slug = slugify(instance.title)

        if commit:
            instance.save()
            instructors = []
            for i in range(1, 4):
                instructor = self.cleaned_data.get(f"instructor_{i}")
                if instructor and instructor not in instructors:
                    instructors.append(instructor)
            instance.instructors.set(instructors)

        return instance
