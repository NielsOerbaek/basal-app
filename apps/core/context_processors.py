from apps.core.decorators import can_manage_signups, can_manage_users


def permissions(request):
    """Add permission checks to template context."""
    user = request.user
    return {
        "can_manage_users": can_manage_users(user),
        "can_manage_signups": can_manage_signups(user),
    }
