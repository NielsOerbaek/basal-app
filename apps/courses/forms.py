from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Column, Div, Field, Layout, Row, Submit
from django import forms
from django.utils import timezone

from apps.schools.models import School

from .models import Course, CourseMaterial, CourseSignUp, Instructor, Location


class CourseForm(forms.ModelForm):
    # Instructor fields - three separate dropdowns with "add new" option
    instructor_1 = forms.ModelChoiceField(
        queryset=Instructor.objects.all().order_by("name"),
        required=True,
        label="Underviser 1",
        empty_label="Vælg underviser...",
    )
    instructor_2 = forms.ModelChoiceField(
        queryset=Instructor.objects.all().order_by("name"),
        required=False,
        label="Underviser 2",
        empty_label="Vælg underviser...",
    )
    instructor_3 = forms.ModelChoiceField(
        queryset=Instructor.objects.all().order_by("name"),
        required=False,
        label="Underviser 3",
        empty_label="Vælg underviser...",
    )

    # "Add new" instructor fields
    new_instructor_1 = forms.CharField(required=False, label="Ny underviser 1")
    new_instructor_2 = forms.CharField(required=False, label="Ny underviser 2")
    new_instructor_3 = forms.CharField(required=False, label="Ny underviser 3")

    # "Add new" location fields
    new_location_name = forms.CharField(required=False, label="Lokationsnavn")
    new_location_street = forms.CharField(required=False, label="Adresse")
    new_location_postal = forms.CharField(required=False, label="Postnummer")
    new_location_municipality = forms.CharField(required=False, label="By")

    class Meta:
        model = Course
        fields = ["start_date", "end_date", "location", "capacity", "is_published", "comment"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "end_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add "add new" option to location choices
        location_choices = [("", "Vælg lokation..."), ("__new__", "+ Tilføj ny lokation")]
        location_choices.extend([(loc.pk, str(loc)) for loc in Location.objects.all().order_by("name")])
        self.fields["location"].choices = location_choices
        self.fields["location"].required = False

        # Add "add new" option to instructor choices
        instructor_choices = [("", "Vælg underviser..."), ("__new__", "+ Tilføj ny underviser")]
        instructor_choices.extend([(inst.pk, inst.name) for inst in Instructor.objects.all().order_by("name")])
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
            Row(
                Column("start_date", css_class="col-md-6"),
                Column("end_date", css_class="col-md-6"),
            ),
            HTML("<h5 class='mt-3'>Lokation</h5>"),
            Row(
                Column("location", css_class="col-md-6"),
            ),
            Div(
                Row(
                    Column("new_location_name", css_class="col-md-6"),
                    Column("new_location_street", css_class="col-md-6"),
                ),
                Row(
                    Column("new_location_postal", css_class="col-md-4"),
                    Column("new_location_municipality", css_class="col-md-8"),
                ),
                css_id="new-location-fields",
                css_class="d-none",
            ),
            HTML("<h5 class='mt-3'>Undervisere</h5>"),
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
            "capacity",
            "is_published",
            "comment",
        )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date:
            if end_date < start_date:
                raise forms.ValidationError("Slutdato kan ikke være før startdato.")

            # Check for duplicate course dates (exclude current instance if editing)
            qs = Course.objects.filter(start_date=start_date, end_date=end_date)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                existing = qs.first()
                raise forms.ValidationError(f'Der findes allerede et kursus med disse datoer: "{existing.display_name}".')

        # Handle "add new" location
        location = self.data.get("location")
        if location == "__new__":
            name = cleaned_data.get("new_location_name")
            street = cleaned_data.get("new_location_street")
            postal = cleaned_data.get("new_location_postal")
            municipality = cleaned_data.get("new_location_municipality")
            if not name:
                self.add_error("new_location_name", "Lokationsnavn er påkrævet")
            else:
                # Create the new location
                new_loc, _ = Location.objects.get_or_create(
                    name=name,
                    defaults={
                        "street_address": street or "",
                        "postal_code": postal or "",
                        "municipality": municipality or "",
                    },
                )
                cleaned_data["location"] = new_loc

        # Handle "add new" instructors
        self._created_instructors = []
        for i in range(1, 4):
            instructor_val = self.data.get(f"instructor_{i}")
            new_name = cleaned_data.get(f"new_instructor_{i}")

            if instructor_val == "__new__":
                if not new_name:
                    self.add_error(f"new_instructor_{i}", "Undervisernavn er påkrævet")
                else:
                    instructor, _ = Instructor.objects.get_or_create(name=new_name)
                    cleaned_data[f"instructor_{i}"] = instructor
                    self._created_instructors.append(instructor)

        # Ensure at least one instructor is selected
        has_instructor = any(cleaned_data.get(f"instructor_{i}") for i in range(1, 4))
        if not has_instructor:
            self.add_error("instructor_1", "Mindst én underviser er påkrævet")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        if commit:
            instance.save()

            # Set instructors from the three fields
            instructors = []
            for i in range(1, 4):
                instructor = self.cleaned_data.get(f"instructor_{i}")
                if instructor and instructor not in instructors:
                    instructors.append(instructor)

            instance.instructors.set(instructors)

        return instance


class CourseMaterialForm(forms.ModelForm):
    class Meta:
        model = CourseMaterial
        fields = ["file", "name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column("file", css_class="col-md-8"),
                Column("name", css_class="col-md-4"),
            ),
        )


class CourseSignUpForm(forms.ModelForm):
    class Meta:
        model = CourseSignUp
        fields = [
            "school",
            "course",
            "participant_name",
            "participant_email",
            "participant_phone",
            "participant_title",
            "is_underviser",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["school"].queryset = School.objects.active()
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "course",
            "school",
            "participant_name",
            Row(
                Column("participant_email", css_class="col-md-6"),
                Column("participant_phone", css_class="col-md-6"),
            ),
            "participant_title",
            "is_underviser",
            Submit("submit", "Gem tilmelding", css_class="btn btn-primary"),
        )


class SchoolChoiceField(forms.ModelChoiceField):
    """Custom field to display school name with kommune."""

    def label_from_instance(self, obj):
        return f"{obj.name} ({obj.kommune})"


class PublicSignUpForm(forms.Form):
    course = forms.ModelChoiceField(
        queryset=Course.objects.filter(is_published=True, start_date__gte=timezone.now().date()),
        label="Vælg et kursus",
        empty_label="Vælg et kursus...",
    )
    school = SchoolChoiceField(
        queryset=School.objects.none(),  # Set dynamically in __init__
        label="Vælg din skole",
        empty_label="Vælg en skole...",
    )
    participant_name = forms.CharField(max_length=255, label="Navn")
    participant_email = forms.EmailField(label="E-mail")
    participant_phone = forms.CharField(max_length=50, required=False, label="Telefon")
    participant_title = forms.CharField(max_length=255, required=False, label="Stilling")
    is_underviser = forms.BooleanField(
        required=False,
        initial=True,
        label="Er underviser",
        help_text="Afkryds hvis deltageren er underviser (ikke leder/andet)",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter schools that are currently enrolled (enrolled_at set, opted_out_at not set)
        self.fields["school"].queryset = (
            School.objects.active().filter(enrolled_at__isnull=False, opted_out_at__isnull=True).order_by("name")
        )
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "course",
            "school",
            HTML("<hr><h5>Deltagerinformation</h5>"),
            "participant_name",
            Row(
                Column("participant_email", css_class="col-md-6"),
                Column("participant_phone", css_class="col-md-6"),
            ),
            "participant_title",
            "is_underviser",
            Submit("submit", "Tilmeld", css_class="btn btn-primary btn-lg"),
        )

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data
