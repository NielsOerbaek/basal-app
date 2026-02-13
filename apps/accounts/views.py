import logging
import secrets
import string

import resend
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.core.decorators import user_admin_required

from .forms import ProfileForm, UserCreateForm, UserUpdateForm

logger = logging.getLogger(__name__)


@method_decorator(user_admin_required, name="dispatch")
class UserListView(ListView):
    model = User
    template_name = "accounts/user_list.html"
    context_object_name = "users"
    paginate_by = 25

    def get_queryset(self):
        queryset = User.objects.order_by("first_name", "last_name", "username")
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
            )
        return queryset


@method_decorator(user_admin_required, name="dispatch")
class UserCreateView(CreateView):
    model = User
    form_class = UserCreateForm
    template_name = "accounts/user_form.html"
    success_url = reverse_lazy("accounts:user-list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Brugeren "{self.object.username}" blev oprettet.')
        return response


@method_decorator(user_admin_required, name="dispatch")
class UserDetailView(DetailView):
    model = User
    template_name = "accounts/user_detail.html"
    context_object_name = "user_obj"


@method_decorator(user_admin_required, name="dispatch")
class UserUpdateView(UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = "accounts/user_form.html"
    context_object_name = "user_obj"

    def get_success_url(self):
        return reverse_lazy("accounts:user-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Brugeren "{self.object.username}" blev opdateret.')
        return response


@method_decorator(user_admin_required, name="dispatch")
class UserToggleActiveView(View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            messages.error(request, "Du kan ikke deaktivere dig selv.")
        else:
            user.is_active = not user.is_active
            user.save()
            status = "aktiveret" if user.is_active else "deaktiveret"
            messages.success(request, f'Brugeren "{user.username}" er blevet {status}.')
        return redirect("accounts:user-list")


def generate_password(length=12):
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def send_password_email(user, new_password):
    """Send password reset email to user."""
    subject = "Din nye adgangskode til Basal"
    html_body = f"""
    <p>Hej {user.first_name or user.username},</p>

    <p>Din adgangskode til Basal er blevet nulstillet.</p>

    <p><strong>Din nye adgangskode er:</strong> {new_password}</p>

    <p>Du kan logge ind på <a href="{settings.SITE_URL}">{settings.SITE_URL}</a></p>

    <p>Vi anbefaler, at du ændrer din adgangskode efter første login.</p>

    <p>Med venlig hilsen,<br>Basal</p>
    """

    # Enforce email domain allowlist
    from apps.emails.services import check_email_domain_allowed

    if not check_email_domain_allowed(user.email):
        logger.warning(
            f"[EMAIL BLOCKED] Recipient {user.email} not in allowed domains: " f"{settings.EMAIL_ALLOWED_DOMAINS}"
        )
        return False

    if not getattr(settings, "RESEND_API_KEY", None):
        # Log to console in development
        logger.info(f"[EMAIL] To: {user.email}")
        logger.info(f"[EMAIL] Subject: {subject}")
        logger.info(f"[EMAIL] New password: {new_password}")
        return True

    try:
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send(
            {
                "from": settings.DEFAULT_FROM_EMAIL,
                "to": [user.email],
                "subject": subject,
                "html": html_body,
            }
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send password reset email: {e}")
        return False


@method_decorator(user_admin_required, name="dispatch")
class UserResetPasswordView(View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)

        if not user.email:
            messages.error(request, f'Brugeren "{user.username}" har ingen e-mailadresse.')
            return redirect("accounts:user-detail", pk=pk)

        # Generate new password
        new_password = generate_password()
        user.set_password(new_password)
        user.save()

        # Send email
        if send_password_email(user, new_password):
            messages.success(request, f"Ny adgangskode er sendt til {user.email}.")
        else:
            messages.error(
                request,
                f"Adgangskoden er nulstillet, men e-mailen kunne ikke sendes. "
                f"Den nye adgangskode er: {new_password}",
            )

        return redirect("accounts:user-detail", pk=pk)


class AccountSettingsView(LoginRequiredMixin, View):
    """View for users to edit their own profile and password."""

    template_name = "accounts/settings.html"

    def get(self, request):
        profile_form = ProfileForm(instance=request.user)
        password_form = PasswordChangeForm(request.user)
        return render(
            request,
            self.template_name,
            {"profile_form": profile_form, "password_form": password_form},
        )

    def post(self, request):
        form_type = request.POST.get("form_type")

        if form_type == "profile":
            profile_form = ProfileForm(request.POST, instance=request.user)
            password_form = PasswordChangeForm(request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profil opdateret.")
                return redirect("accounts:settings")
        elif form_type == "password":
            profile_form = ProfileForm(instance=request.user)
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Adgangskode ændret.")
                return redirect("accounts:settings")
        else:
            profile_form = ProfileForm(instance=request.user)
            password_form = PasswordChangeForm(request.user)

        return render(
            request,
            self.template_name,
            {"profile_form": profile_form, "password_form": password_form},
        )
