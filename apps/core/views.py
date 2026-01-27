from pathlib import Path

import markdown
from django.conf import settings
from django.core.management import call_command
from django.db.models import Count
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
from django.views import View
from django.views.generic import TemplateView

from apps.contacts.models import ContactTime
from apps.courses.models import Course, CourseSignUp
from apps.goals.calculations import get_current_school_year, get_metrics_for_year
from apps.goals.constants import PROJECT_TARGETS
from apps.schools.models import School

from .decorators import staff_required


@method_decorator(staff_required, name="dispatch")
class DashboardView(TemplateView):
    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()

        context["upcoming_courses"] = (
            Course.objects.filter(start_date__gte=now.date())
            .annotate(signup_count_value=Count("signups"))
            .order_by("start_date")[:5]
        )

        context["recent_contacts"] = ContactTime.objects.select_related("school", "created_by")[:10]

        context["recent_signups"] = CourseSignUp.objects.select_related("school", "course")[:10]

        context["recent_enrollments"] = (
            School.objects.active()
            .filter(enrolled_at__isnull=False)
            .prefetch_related("people")
            .order_by("-enrolled_at")[:10]
        )

        # Project goals summary for current year
        current_year = get_current_school_year()
        metrics = get_metrics_for_year(current_year)
        targets = PROJECT_TARGETS.get(current_year, {})
        context["project_goals"] = {
            "current_year": current_year,
            "metrics": metrics,
            "targets": targets,
        }

        return context


def verify_cron_token(request):
    """Verify CRON_SECRET token from header or query param."""
    cron_secret = getattr(settings, "CRON_SECRET", None)
    if not cron_secret:
        return False, JsonResponse({"error": "CRON_SECRET not configured"}, status=500)

    auth_header = request.headers.get("Authorization", "")
    token_param = request.GET.get("token", "")

    provided_token = None
    if auth_header.startswith("Bearer "):
        provided_token = auth_header[7:]
    elif token_param:
        provided_token = token_param

    if provided_token != cron_secret:
        return False, JsonResponse({"error": "Unauthorized"}, status=401)

    return True, None


class CronSendRemindersView(View):
    """
    Protected endpoint for sending course reminders via cron job.
    Requires CRON_SECRET token in Authorization header or query param.
    """

    def get(self, request):
        valid, error_response = verify_cron_token(request)
        if not valid:
            return error_response

        from io import StringIO

        output = StringIO()

        try:
            call_command("send_course_reminders", stdout=output)
            return JsonResponse(
                {
                    "success": True,
                    "output": output.getvalue(),
                }
            )
        except Exception as e:
            return JsonResponse(
                {
                    "success": False,
                    "error": str(e),
                },
                status=500,
            )


class CronBackupView(View):
    """
    Protected endpoint for database and media backup via cron job.
    Requires CRON_SECRET token in Authorization header or query param.
    """

    def get(self, request):
        valid, error_response = verify_cron_token(request)
        if not valid:
            return error_response

        from io import StringIO

        output = StringIO()
        error_output = StringIO()

        try:
            call_command("backup", stdout=output, stderr=error_output)
            return JsonResponse(
                {
                    "success": True,
                    "output": output.getvalue(),
                    "errors": error_output.getvalue() or None,
                }
            )
        except Exception as e:
            return JsonResponse(
                {
                    "success": False,
                    "error": str(e),
                    "output": output.getvalue(),
                },
                status=500,
            )


@method_decorator(staff_required, name="dispatch")
class AboutView(TemplateView):
    """About page showing the changelog."""

    template_name = "core/about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Read changelog from project root
        changelog_path = Path(settings.BASE_DIR) / "CHANGELOG.md"
        if changelog_path.exists():
            changelog_md = changelog_path.read_text(encoding="utf-8")
            changelog_html = markdown.markdown(changelog_md, extensions=["tables", "fenced_code"])
            context["changelog"] = mark_safe(changelog_html)
        else:
            context["changelog"] = None

        return context
