from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML
from django import forms
from django.utils import timezone

from apps.schools.models import School

from .models import Course, CourseSignUp


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'start_date', 'end_date', 'location', 'undervisere', 'capacity', 'is_published', 'comment']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'title',
            Row(
                Column('start_date', css_class='col-md-6'),
                Column('end_date', css_class='col-md-6'),
            ),
            Row(
                Column('location', css_class='col-md-6'),
                Column('undervisere', css_class='col-md-6'),
            ),
            'capacity',
            'is_published',
            'comment',
            Submit('submit', 'Gem kursus', css_class='btn btn-primary'),
        )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError('Slutdato kan ikke være før startdato.')
        return cleaned_data


class CourseSignUpForm(forms.ModelForm):
    class Meta:
        model = CourseSignUp
        fields = ['school', 'course', 'participant_name', 'participant_email', 'participant_title']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['school'].queryset = School.objects.active()
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'course',
            'school',
            'participant_name',
            Row(
                Column('participant_email', css_class='col-md-6'),
                Column('participant_title', css_class='col-md-6'),
            ),
            Submit('submit', 'Gem tilmelding', css_class='btn btn-primary'),
        )


class PublicSignUpForm(forms.Form):
    course = forms.ModelChoiceField(
        queryset=Course.objects.filter(is_published=True, start_date__gte=timezone.now().date()),
        label='Vælg et kursus',
        empty_label='Vælg et kursus...'
    )
    school = forms.ModelChoiceField(
        queryset=School.objects.active(),
        label='Vælg din skole',
        empty_label='Vælg en skole...'
    )
    participant_name = forms.CharField(max_length=255, label='Navn')
    participant_email = forms.EmailField(label='E-mail')
    participant_title = forms.CharField(max_length=255, required=False, label='Stilling')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'course',
            'school',
            HTML('<hr><h5>Deltagerinformation</h5>'),
            'participant_name',
            Row(
                Column('participant_email', css_class='col-md-6'),
                Column('participant_title', css_class='col-md-6'),
            ),
            Submit('submit', 'Tilmeld', css_class='btn btn-primary btn-lg'),
        )

    def clean(self):
        cleaned_data = super().clean()
        school = cleaned_data.get('school')

        if school and not school.has_available_seats:
            raise forms.ValidationError(
                'Din skole har ikke flere ubrugte pladser. '
                'Kontakt venligst Basal for at købe flere pladser.'
            )

        return cleaned_data
