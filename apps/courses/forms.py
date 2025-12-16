from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML
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
        label='Vælg din skole',
        empty_label='Vælg en skole...'
    )
    participant_name = forms.CharField(max_length=255, label='Dit navn')
    participant_title = forms.CharField(max_length=255, required=False, label='Din jobtitel')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'course',
            'school',
            HTML('<hr><h5>Deltagerinformation</h5>'),
            Row(
                Column('participant_name', css_class='col-md-6'),
                Column('participant_title', css_class='col-md-6'),
            ),
            Submit('submit', 'Tilmeld', css_class='btn btn-primary btn-lg'),
        )
