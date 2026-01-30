"""Utility functions for courses app."""

# Danish month abbreviations (lowercase)
DANISH_MONTHS = {
    1: "jan",
    2: "feb",
    3: "mar",
    4: "apr",
    5: "maj",
    6: "jun",
    7: "jul",
    8: "aug",
    9: "sep",
    10: "okt",
    11: "nov",
    12: "dec",
}


def format_date_danish(d, include_year=True):
    """Format a date in Danish locale.

    Args:
        d: A date object
        include_year: Whether to include the year in the output

    Returns:
        Formatted date string like "15. jan 2025" or "15. jan"
    """
    month = DANISH_MONTHS[d.month]
    if include_year:
        return f"{d.day}. {month} {d.year}"
    return f"{d.day}. {month}"
