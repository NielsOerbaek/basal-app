from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit
from django import forms
from django.contrib.auth.models import User


class UserCreateForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Adgangskode',
        widget=forms.PasswordInput,
        help_text='Indtast en stærk adgangskode.'
    )
    password2 = forms.CharField(
        label='Bekræft adgangskode',
        widget=forms.PasswordInput,
        help_text='Indtast den samme adgangskode igen.'
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_staff', 'is_superuser']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'username',
            Row(
                Column('first_name', css_class='col-md-6'),
                Column('last_name', css_class='col-md-6'),
            ),
            'email',
            Row(
                Column('password1', css_class='col-md-6'),
                Column('password2', css_class='col-md-6'),
            ),
            Row(
                Column('is_staff', css_class='col-md-6'),
                Column('is_superuser', css_class='col-md-6'),
            ),
            Submit('submit', 'Opret bruger', css_class='btn btn-primary'),
        )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Adgangskoderne matcher ikke.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'is_superuser']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'username',
            Row(
                Column('first_name', css_class='col-md-6'),
                Column('last_name', css_class='col-md-6'),
            ),
            'email',
            Row(
                Column('is_active', css_class='col-md-4'),
                Column('is_staff', css_class='col-md-4'),
                Column('is_superuser', css_class='col-md-4'),
            ),
            Submit('submit', 'Gem ændringer', css_class='btn btn-primary'),
        )
