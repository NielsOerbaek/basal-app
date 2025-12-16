from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, Div, HTML, Field
from django import forms
from django.utils import timezone

from apps.schools.models import School

from .models import Course, CourseSignUp


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'datetime', 'location', 'capacity', 'is_published', 'comment']
        widgets = {
            'datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'title',
            Row(
                Column('datetime', css_class='col-md-6'),
                Column('location', css_class='col-md-6'),
            ),
            Row(
                Column('capacity', css_class='col-md-6'),
                Column('is_published', css_class='col-md-6'),
            ),
            'comment',
            Submit('submit', 'Gem kursus', css_class='btn btn-primary'),
        )


class CourseSignUpForm(forms.ModelForm):
    class Meta:
        model = CourseSignUp
        fields = ['school', 'course', 'participant_name', 'participant_title']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['school'].queryset = School.objects.active()
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'course',
            'school',
            Row(
                Column('participant_name', css_class='col-md-6'),
                Column('participant_title', css_class='col-md-6'),
            ),
            Submit('submit', 'Gem tilmelding', css_class='btn btn-primary'),
        )


class PublicSignUpForm(forms.Form):
    course = forms.ModelChoiceField(
        queryset=Course.objects.filter(is_published=True, datetime__gte=timezone.now()),
        label='Vælg et kursus',
        empty_label='Vælg et kursus...'
    )
    school = forms.ModelChoiceField(
        queryset=School.objects.active(),
        required=False,
        label='Vælg din skole',
        empty_label='Vælg din skole eller registrer en ny...'
    )
    new_school_name = forms.CharField(max_length=255, required=False, label='Skolenavn')
    new_school_location = forms.CharField(max_length=255, required=False, label='Adresse')
    new_school_contact_name = forms.CharField(max_length=255, required=False, label='Kontaktperson')
    new_school_contact_email = forms.EmailField(required=False, label='Kontakt e-mail')
    new_school_contact_phone = forms.CharField(max_length=50, required=False, label='Kontakt telefon')
    participant_name = forms.CharField(max_length=255, label='Dit navn')
    participant_title = forms.CharField(max_length=255, required=False, label='Din jobtitel')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'course',
            HTML('<hr><h5>Skoleinformation</h5>'),
            'school',
            Div(
                HTML('<p class="text-muted small">Eller registrer en ny skole:</p>'),
                'new_school_name',
                'new_school_location',
                Row(
                    Column('new_school_contact_name', css_class='col-md-6'),
                    Column('new_school_contact_email', css_class='col-md-6'),
                ),
                'new_school_contact_phone',
                css_id='new-school-fields',
            ),
            HTML('<hr><h5>Deltagerinformation</h5>'),
            Row(
                Column('participant_name', css_class='col-md-6'),
                Column('participant_title', css_class='col-md-6'),
            ),
            Submit('submit', 'Tilmeld', css_class='btn btn-primary btn-lg'),
        )

    def clean(self):
        cleaned_data = super().clean()
        school = cleaned_data.get('school')
        new_school_name = cleaned_data.get('new_school_name')

        if not school and not new_school_name:
            raise forms.ValidationError('Vælg venligst en eksisterende skole eller indtast oplysninger om en ny skole.')

        if not school:
            if not cleaned_data.get('new_school_location'):
                self.add_error('new_school_location', 'Dette felt er påkrævet for nye skoler.')
            if not cleaned_data.get('new_school_contact_name'):
                self.add_error('new_school_contact_name', 'Dette felt er påkrævet for nye skoler.')
            if not cleaned_data.get('new_school_contact_email'):
                self.add_error('new_school_contact_email', 'Dette felt er påkrævet for nye skoler.')

        return cleaned_data
