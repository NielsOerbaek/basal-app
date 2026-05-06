from apps.schools.models import School

# Shared session key — webinar flow reuses this so a single school login
# carries across both course and webinar signups in the same browser.
SCHOOL_SESSION_KEY = "course_signup_school_id"


def resolve_signup_auth(request):
    """
    Determine which school (if any) the request is authenticated as for a
    public signup flow. Used by both course and webinar signup views.

    Returns a dict with:
      - auth_mode: "staff" | "token" | "session" | None
      - locked_school: School | None
      - show_password_form: bool
      - auth_error: str | None
    """
    # Allow ?clear=1 to forget the session school
    if request.GET.get("clear") == "1":
        if SCHOOL_SESSION_KEY in request.session:
            del request.session[SCHOOL_SESSION_KEY]

    # Staff bypass — full access
    if request.user.is_authenticated and request.user.is_staff:
        return {
            "auth_mode": "staff",
            "locked_school": None,
            "show_password_form": False,
            "auth_error": None,
        }

    # Token in URL
    token = request.GET.get("token", "").strip()
    if token:
        try:
            school = School.objects.get(
                signup_token=token,
                enrolled_at__isnull=False,
                opted_out_at__isnull=True,
            )
            request.session[SCHOOL_SESSION_KEY] = school.pk
            return {
                "auth_mode": "token",
                "locked_school": school,
                "show_password_form": False,
                "auth_error": None,
            }
        except School.DoesNotExist:
            return {
                "auth_mode": None,
                "locked_school": None,
                "show_password_form": True,
                "auth_error": "Ugyldigt link. Brug venligst koden fra jeres velkomstmail.",
            }

    # Session
    school_id = request.session.get(SCHOOL_SESSION_KEY)
    if school_id:
        try:
            school = School.objects.get(
                pk=school_id,
                enrolled_at__isnull=False,
                opted_out_at__isnull=True,
            )
            return {
                "auth_mode": "session",
                "locked_school": school,
                "show_password_form": False,
                "auth_error": None,
            }
        except School.DoesNotExist:
            del request.session[SCHOOL_SESSION_KEY]

    # Not authenticated
    return {
        "auth_mode": None,
        "locked_school": None,
        "show_password_form": True,
        "auth_error": None,
    }
