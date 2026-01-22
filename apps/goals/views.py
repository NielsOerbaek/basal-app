from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, View

from apps.core.decorators import staff_required
from apps.core.models import ProjectSettings

from .calculations import get_current_school_year, get_metrics_for_year
from .constants import PROJECT_TARGETS, PROJECT_TOTALS, PROJECT_YEARS


@method_decorator(staff_required, name="dispatch")
class ProjectGoalsView(TemplateView):
    """Full 5-year project goals detail page."""

    template_name = "goals/project_goals.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        settings = ProjectSettings.get()
        current_year = get_current_school_year()
        current_year_idx = PROJECT_YEARS.index(current_year) if current_year in PROJECT_YEARS else -1

        # Build data for each year
        years_data = []
        for idx, year in enumerate(PROJECT_YEARS):
            is_future = idx > current_year_idx if current_year_idx >= 0 else False
            metrics = get_metrics_for_year(year) if not is_future else None
            targets = PROJECT_TARGETS[year]
            # URL-friendly year format: 2024/25 -> 2024-25
            url_year = year.replace("/", "-")
            # Calculate goal achievement status for each metric
            goal_met = None
            if metrics:
                goal_met = {
                    "new_schools": metrics["new_schools"] >= targets["new_schools"],
                    "anchoring": metrics["anchoring"] >= targets["anchoring"],
                    "courses": metrics["courses"] >= targets["courses"],
                    "trained_total": metrics["trained_total"] >= targets["trained_total"],
                    "trained_teachers": metrics["trained_teachers"] >= targets["trained_teachers"],
                    "klasseforloeb": metrics["klasseforloeb"] >= targets["klasseforloeb_min"],
                    "students": metrics["students"] >= targets["students_min"],
                }
            years_data.append(
                {
                    "year": year,
                    "url_year": url_year,
                    "is_current": year == current_year,
                    "is_future": is_future,
                    "metrics": metrics,
                    "targets": targets,
                    "goal_met": goal_met,
                }
            )

        # Calculate actual totals (only for non-future years)
        past_and_current = [y for y in years_data if not y["is_future"]]
        actual_totals = {
            "new_schools": sum(y["metrics"]["new_schools"] for y in past_and_current),
            "anchoring": sum(y["metrics"]["anchoring"] for y in past_and_current),
            "courses": sum(y["metrics"]["courses"] for y in past_and_current),
            "trained_total": sum(y["metrics"]["trained_total"] for y in past_and_current),
            "trained_teachers": sum(y["metrics"]["trained_teachers"] for y in past_and_current),
            "klasseforloeb": sum(y["metrics"]["klasseforloeb"] for y in past_and_current),
            "students": sum(y["metrics"]["students"] for y in past_and_current),
        }

        # Calculate goal achievement for totals
        totals_goal_met = {
            "new_schools": actual_totals["new_schools"] >= PROJECT_TOTALS["new_schools"],
            "anchoring": actual_totals["anchoring"] >= PROJECT_TOTALS["anchoring"],
            "courses": actual_totals["courses"] >= PROJECT_TOTALS["courses"],
            "trained_total": actual_totals["trained_total"] >= PROJECT_TOTALS["trained_total"],
            "trained_teachers": actual_totals["trained_teachers"] >= PROJECT_TOTALS["trained_teachers"],
            "klasseforloeb": actual_totals["klasseforloeb"] >= PROJECT_TOTALS["klasseforloeb_min"],
            "students": actual_totals["students"] >= PROJECT_TOTALS["students_min"],
        }

        context["years_data"] = years_data
        context["project_totals"] = PROJECT_TOTALS
        context["actual_totals"] = actual_totals
        context["totals_goal_met"] = totals_goal_met
        context["settings"] = settings
        context["current_year"] = current_year

        return context


@method_decorator(staff_required, name="dispatch")
class ProjectSettingsUpdateView(View):
    """HTMX view for updating ProjectSettings multipliers."""

    def post(self, request):
        settings = ProjectSettings.get()

        try:
            klasseforloeb = request.POST.get("klasseforloeb_per_teacher_per_year")
            students = request.POST.get("students_per_klasseforloeb")

            if klasseforloeb:
                settings.klasseforloeb_per_teacher_per_year = klasseforloeb
            if students:
                settings.students_per_klasseforloeb = students

            settings.save()
        except (ValueError, TypeError):
            pass  # Ignore invalid input

        # Redirect back to project goals page
        return redirect("goals:project-goals")
