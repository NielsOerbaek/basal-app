"""
School Year Helper API

This module provides the canonical interface for working with school years.
All school year logic should go through these functions.

School years:
- Run from August 1 to July 31
- Use "YYYY/YY" format (e.g., "2024/25")
- Are stored in the SchoolYear model as the single source of truth

Usage:
    from apps.schools.school_years import get_current_school_year, get_school_year_for_date

    # Get current school year as SchoolYear instance
    current = get_current_school_year()

    # Get school year for a specific date
    sy = get_school_year_for_date(some_date)

    # Format/parse helpers
    name = format_school_year(2024)  # "2024/25"
    start_year = parse_school_year("2024/25")  # 2024
"""

from datetime import date
from typing import TYPE_CHECKING, Optional

from django.core.exceptions import ObjectDoesNotExist

if TYPE_CHECKING:
    from apps.schools.models import SchoolYear

# Canonical format: "YYYY/YY" (e.g., "2024/25")
SCHOOL_YEAR_FORMAT = "{start_year}/{end_year_short}"


def format_school_year(start_year: int) -> str:
    """
    Format a start year into canonical school year string.

    Args:
        start_year: The year the school year starts (e.g., 2024)

    Returns:
        Canonical format string (e.g., "2024/25")

    Example:
        >>> format_school_year(2024)
        '2024/25'
    """
    end_year_short = str(start_year + 1)[2:]
    return f"{start_year}/{end_year_short}"


def parse_school_year(year_str: str) -> int:
    """
    Parse a school year string into its start year.

    Handles multiple formats for input flexibility:
    - "2024/25" (canonical)
    - "2024-25" (URL format)
    - "2024-2025" (full hyphenated)

    Args:
        year_str: School year string in any supported format

    Returns:
        The start year as integer (e.g., 2024)

    Raises:
        ValueError: If the string cannot be parsed

    Example:
        >>> parse_school_year("2024/25")
        2024
        >>> parse_school_year("2024-25")
        2024
    """
    year_str = year_str.strip()

    # Try canonical format "2024/25"
    if "/" in year_str and len(year_str) == 7:
        return int(year_str[:4])

    # Try short hyphenated "2024-25"
    if "-" in year_str and len(year_str) == 7:
        return int(year_str[:4])

    # Try full hyphenated "2024-2025"
    if "-" in year_str and len(year_str) == 9:
        return int(year_str[:4])

    raise ValueError(f"Cannot parse school year string: {year_str!r}")


def normalize_school_year(year_str: str) -> str:
    """
    Normalize any school year string to canonical format.

    Use this when accepting user input or URL parameters.

    Args:
        year_str: School year in any supported format

    Returns:
        Canonical format string (e.g., "2024/25")

    Example:
        >>> normalize_school_year("2024-25")
        '2024/25'
        >>> normalize_school_year("2024-2025")
        '2024/25'
    """
    start_year = parse_school_year(year_str)
    return format_school_year(start_year)


def get_school_year_dates(year_str: str) -> tuple[date, date]:
    """
    Get start and end dates for a school year string.

    Args:
        year_str: School year in any supported format

    Returns:
        Tuple of (start_date, end_date)
        - start_date: August 1 of start year
        - end_date: July 31 of end year

    Example:
        >>> get_school_year_dates("2024/25")
        (date(2024, 8, 1), date(2025, 7, 31))
    """
    start_year = parse_school_year(year_str)
    return (date(start_year, 8, 1), date(start_year + 1, 7, 31))


def calculate_school_year_for_date(d: date) -> str:
    """
    Calculate which school year a date falls into.

    This is a pure calculation - does not touch the database.

    Args:
        d: The date to check

    Returns:
        School year name in canonical format

    Example:
        >>> calculate_school_year_for_date(date(2024, 9, 15))
        '2024/25'
        >>> calculate_school_year_for_date(date(2024, 3, 15))
        '2023/24'
    """
    if d.month >= 8:
        start_year = d.year
    else:
        start_year = d.year - 1
    return format_school_year(start_year)


def get_school_year_for_date(d: date) -> "SchoolYear":
    """
    Get the SchoolYear instance for a given date.

    Args:
        d: The date to look up

    Returns:
        SchoolYear instance

    Raises:
        SchoolYear.DoesNotExist: If no matching school year exists in database
    """
    from apps.schools.models import SchoolYear

    return SchoolYear.objects.get(start_date__lte=d, end_date__gte=d)


def get_current_school_year(d: Optional[date] = None) -> "SchoolYear":
    """
    Get the current SchoolYear instance.

    Args:
        d: Optional date to use instead of today (useful for testing)

    Returns:
        SchoolYear instance for the current (or specified) date

    Raises:
        SchoolYear.DoesNotExist: If no matching school year exists in database
    """
    if d is None:
        d = date.today()
    return get_school_year_for_date(d)


def get_school_year_by_name(name: str) -> "SchoolYear":
    """
    Get a SchoolYear instance by its name.

    Accepts any supported format and normalizes it.

    Args:
        name: School year name in any supported format

    Returns:
        SchoolYear instance

    Raises:
        SchoolYear.DoesNotExist: If no matching school year exists
    """
    from apps.schools.models import SchoolYear

    canonical_name = normalize_school_year(name)
    return SchoolYear.objects.get(name=canonical_name)


def get_or_none(name: str) -> Optional["SchoolYear"]:
    """
    Get a SchoolYear by name, returning None if not found.

    Convenience wrapper that doesn't raise exceptions.

    Args:
        name: School year name in any supported format

    Returns:
        SchoolYear instance or None
    """
    try:
        return get_school_year_by_name(name)
    except (ObjectDoesNotExist, ValueError):
        return None


def iter_school_years(start: str, end: str, inclusive: bool = True):
    """
    Iterate over SchoolYear instances in a range.

    Args:
        start: Start year name (e.g., "2024/25")
        end: End year name (e.g., "2028/29")
        inclusive: Include end year (default True)

    Yields:
        SchoolYear instances in order

    Example:
        >>> for sy in iter_school_years("2024/25", "2026/27"):
        ...     print(sy.name)
        2024/25
        2025/26
        2026/27
    """
    from apps.schools.models import SchoolYear

    start_year = parse_school_year(start)
    end_year = parse_school_year(end)

    if not inclusive:
        end_year -= 1

    for year in range(start_year, end_year + 1):
        name = format_school_year(year)
        try:
            yield SchoolYear.objects.get(name=name)
        except ObjectDoesNotExist:
            continue
