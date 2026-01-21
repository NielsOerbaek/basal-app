from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def staff_required(view_func):
    """
    Decorator that requires the user to be logged in and a staff member.
    Redirects to the regular login page (not admin) if not authenticated.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return login_required(_wrapped_view)


def user_admin_required(view_func):
    """
    Decorator that requires the user to be a user administrator.
    User must be in 'Brugeradministrator' group or be a superuser.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not can_manage_users(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return login_required(_wrapped_view)


def signup_admin_required(view_func):
    """
    Decorator that requires the user to be a signup administrator.
    User must be in 'Tilmeldingsadministrator' group or be a superuser.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not can_manage_signups(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return login_required(_wrapped_view)


def can_manage_users(user):
    """Check if user can manage other users."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name="Brugeradministrator").exists()


def can_manage_signups(user):
    """Check if user can manage signup pages."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name="Tilmeldingsadministrator").exists()
