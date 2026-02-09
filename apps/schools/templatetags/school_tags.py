from django import template
from django.utils.html import format_html

from apps.schools.school_years import calculate_school_year_for_date, parse_school_year

register = template.Library()

# Cycling colors based on start_year % 8
YEAR_COLORS = {
    0: ("#6f42c1", "#ffffff"),  # purple
    1: ("#0d6efd", "#ffffff"),  # blue
    2: ("#198754", "#ffffff"),  # green
    3: ("#fd7e14", "#ffffff"),  # orange
    4: ("#dc3545", "#ffffff"),  # red
    5: ("#20c997", "#ffffff"),  # teal
    6: ("#d63384", "#ffffff"),  # pink
    7: ("#ffc107", "#212529"),  # yellow, dark text
}


@register.simple_tag
def school_year_chip(active_from):
    """
    Render a colored Bootstrap badge showing the school year name.

    Usage: {% school_year_chip school.active_from %}
    """
    if active_from is None:
        return ""

    year_name = calculate_school_year_for_date(active_from)
    start_year = parse_school_year(year_name)
    bg_color, text_color = YEAR_COLORS[start_year % 8]

    return format_html(
        '<span class="badge" style="background-color: {}; color: {}">{}</span>',
        bg_color,
        text_color,
        year_name,
    )
