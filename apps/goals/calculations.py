"""
Calculation functions for project goals metrics.
"""

from datetime import date

from apps.core.models import ProjectSettings
from apps.courses.models import AttendanceStatus, Course, CourseSignUp
from apps.schools.models import School
from apps.schools.school_years import (
    calculate_school_year_for_date,
    get_school_year_dates,
)


def get_current_school_year() -> str:
    """Returns the current school year as a string (e.g., '2024/25')."""
    return calculate_school_year_for_date(date.today())


def get_metrics_for_year(year_str: str) -> dict:
    """
    Calculate all metrics for a given school year.

    Returns dict with:
    - new_schools: Schools enrolled in this year
    - anchoring: Schools enrolled before this year, still active
    - courses: Number of courses in this year
    - trained_total: Participants who attended courses
    - trained_teachers: Teachers (is_underviser=True) who attended
    - klasseforloeb: Estimated class sequences (calculated)
    - students: Estimated students reached (calculated)
    """
    start_date, end_date = get_school_year_dates(year_str)
    settings = ProjectSettings.get()

    # New school partnerships: enrolled this year
    new_schools = School.objects.active().filter(enrolled_at__gte=start_date, enrolled_at__lte=end_date).count()

    # Anchoring: enrolled before this year, still active (not opted out)
    anchoring_schools = (
        School.objects.active()
        .filter(
            enrolled_at__lt=start_date,
            enrolled_at__isnull=False,
        )
        .exclude(
            opted_out_at__lte=end_date  # Exclude schools that opted out before end of year
        )
        .count()
    )

    # Courses in this school year
    year_courses = Course.objects.filter(start_date__gte=start_date, start_date__lte=end_date)
    courses_count = year_courses.count()

    # Trained participants (attended = PRESENT via roll-call)
    trained_total = CourseSignUp.objects.filter(course__in=year_courses, attendance=AttendanceStatus.PRESENT).count()

    # Trained teachers only
    trained_teachers = CourseSignUp.objects.filter(
        course__in=year_courses, attendance=AttendanceStatus.PRESENT, is_underviser=True
    ).count()

    # Calculated estimates
    klasseforloeb = trained_teachers * settings.klasseforloeb_per_teacher_per_year
    students = klasseforloeb * settings.students_per_klasseforloeb

    return {
        "new_schools": new_schools,
        "anchoring": anchoring_schools,
        "courses": courses_count,
        "trained_total": trained_total,
        "trained_teachers": trained_teachers,
        "klasseforloeb": klasseforloeb,
        "students": students,
    }


def get_cumulative_metrics() -> dict:
    """
    Calculate cumulative (total) metrics across all project years.

    Returns dict with totals for each metric.
    """
    from .constants import PROJECT_YEARS

    totals = {
        "new_schools": 0,
        "anchoring": 0,
        "courses": 0,
        "trained_total": 0,
        "trained_teachers": 0,
        "klasseforloeb": 0,
        "students": 0,
    }

    for year in PROJECT_YEARS:
        metrics = get_metrics_for_year(year)
        for key in totals:
            totals[key] += metrics[key]

    return totals
