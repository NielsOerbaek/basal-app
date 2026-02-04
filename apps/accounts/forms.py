from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Column, Layout, Row, Submit
from django import forms
from django.contrib.auth.models import Group, User


class UserPermissionMixin:
    """Mixin to handle permission fields for user forms."""

    def _get_permissions(self, user):
        """Get current permissions as dict of booleans."""
        return {
            "is_user_admin": user.groups.filter(name="Brugeradministrator").exists(),
            "is_signup_admin": user.groups.filter(name="Tilmeldingsadministrator").exists(),
            "is_full_admin": user.is_superuser,
        }

    def _apply_permissions(self, user, is_user_admin, is_signup_admin, is_full_admin):
        """Apply the selected permissions to a user."""
        # Get or create the groups
        user_admin_group, _ = Group.objects.get_or_create(name="Brugeradministrator")
        signup_admin_group, _ = Group.objects.get_or_create(name="Tilmeldingsadministrator")

        # Clear existing permission groups
        user.groups.remove(user_admin_group, signup_admin_group)

        # All users need is_staff to access the app
        user.is_staff = True

        if is_full_admin:
            user.is_superuser = True
        else:
            user.is_superuser = False
            if is_user_admin:
                user.groups.add(user_admin_group)
            if is_signup_admin:
                user.groups.add(signup_admin_group)

        user.save()


class UserCreateForm(UserPermissionMixin, forms.ModelForm):
    password1 = forms.CharField(
        label="Adgangskode", widget=forms.PasswordInput, help_text="Indtast en stærk adgangskode."
    )
    password2 = forms.CharField(
        label="Bekræft adgangskode", widget=forms.PasswordInput, help_text="Indtast den samme adgangskode igen."
    )
    is_user_admin = forms.BooleanField(
        label="Brugeradministrator",
        required=False,
        help_text="Kan oprette, redigere og deaktivere brugere samt nulstille adgangskoder.",
    )
    is_signup_admin = forms.BooleanField(
        label="Tilmeldingsadministrator",
        required=False,
        help_text="Kan redigere tilmeldingssider, formulartekster og vedhæftede dokumenter.",
    )
    is_full_admin = forms.BooleanField(
        label="Fuld administrator",
        required=False,
        help_text="Har adgang til alt, inklusiv Django admin og systemindstillinger.",
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "username",
            Row(
                Column("first_name", css_class="col-md-6"),
                Column("last_name", css_class="col-md-6"),
            ),
            "email",
            Row(
                Column("password1", css_class="col-md-6"),
                Column("password2", css_class="col-md-6"),
            ),
            HTML("<hr><h5>Rettigheder</h5>"),
            "is_user_admin",
            "is_signup_admin",
            "is_full_admin",
            Submit("submit", "Opret bruger", css_class="btn btn-primary mt-3"),
        )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Adgangskoderne matcher ikke.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            self._apply_permissions(
                user,
                self.cleaned_data.get("is_user_admin", False),
                self.cleaned_data.get("is_signup_admin", False),
                self.cleaned_data.get("is_full_admin", False),
            )
        return user


class UserUpdateForm(UserPermissionMixin, forms.ModelForm):
    is_user_admin = forms.BooleanField(
        label="Brugeradministrator",
        required=False,
        help_text="Kan oprette, redigere og deaktivere brugere samt nulstille adgangskoder.",
    )
    is_signup_admin = forms.BooleanField(
        label="Tilmeldingsadministrator",
        required=False,
        help_text="Kan redigere tilmeldingssider, formulartekster og vedhæftede dokumenter.",
    )
    is_full_admin = forms.BooleanField(
        label="Fuld administrator",
        required=False,
        help_text="Har adgang til alt, inklusiv Django admin og systemindstillinger.",
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial permission values based on current user state
        if self.instance and self.instance.pk:
            perms = self._get_permissions(self.instance)
            self.fields["is_user_admin"].initial = perms["is_user_admin"]
            self.fields["is_signup_admin"].initial = perms["is_signup_admin"]
            self.fields["is_full_admin"].initial = perms["is_full_admin"]

        self.helper = FormHelper()
        self.helper.layout = Layout(
            "username",
            Row(
                Column("first_name", css_class="col-md-6"),
                Column("last_name", css_class="col-md-6"),
            ),
            "email",
            "is_active",
            HTML("<hr><h5>Rettigheder</h5>"),
            "is_user_admin",
            "is_signup_admin",
            "is_full_admin",
            Submit("submit", "Gem ændringer", css_class="btn btn-primary mt-3"),
        )

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            self._apply_permissions(
                user,
                self.cleaned_data.get("is_user_admin", False),
                self.cleaned_data.get("is_signup_admin", False),
                self.cleaned_data.get("is_full_admin", False),
            )
        return user


class ProfileForm(forms.ModelForm):
    """Form for users to edit their own profile."""

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column("username", css_class="col-md-6"),
                Column("email", css_class="col-md-6"),
            ),
            Row(
                Column("first_name", css_class="col-md-6"),
                Column("last_name", css_class="col-md-6"),
            ),
        )
