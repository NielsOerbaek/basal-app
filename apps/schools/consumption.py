FORANKRINGSPLADS_VALID_UNTIL = "2028/29"
MEMBERSHIP_PRICE = 1450
SEAT_PRICES = {1: 7995, 2: 15190, 3: 21586}
SEAT_BULK_UNIT_PRICE = 7195


def calculate_seat_price(n: int) -> int:
    """Price for n purchased (non-free) seats in a school year."""
    if n <= 0:
        return 0
    return SEAT_PRICES.get(n, n * SEAT_BULK_UNIT_PRICE)


def get_consumption_overview(school, today=None):
    """
    Returns the consumption overview data structure for a school.
    Returns None if school is not enrolled or has no active_from date.
    """
    from datetime import date

    if today is None:
        today = date.today()

    if not school.active_from or not school.is_enrolled:
        return None

    from apps.courses.models import Course
    from apps.schools.school_years import (
        calculate_school_year_for_date,
        format_school_year,
        get_school_year_dates,
        parse_school_year,
    )

    first_year_name = school.get_first_school_year()
    first_year_start, first_year_end = get_school_year_dates(first_year_name)
    current_year_name = calculate_school_year_for_date(today)

    first_year_int = parse_school_year(first_year_name)
    current_year_int = parse_school_year(current_year_name)
    next_year_int = current_year_int + 1

    # All school year names to display: first_year → next_year (inclusive)
    year_names = [format_school_year(y) for y in range(first_year_int, next_year_int + 1)]

    # Load all signups ordered by course start_date
    all_signups = list(school.course_signups.select_related("course").order_by("course__start_date"))

    # Forankringsplads: consumed by first signup after year 1
    post_first_year_signups = [s for s in all_signups if s.course.start_date > first_year_end]
    forankringsplads_used = len(post_first_year_signups) > 0
    forankringsplads_year = None
    if post_first_year_signups:
        forankringsplads_year = calculate_school_year_for_date(post_first_year_signups[0].course.start_date)

    # School qualifies for forankringsplads if it's past its first year
    is_continuation = first_year_int < current_year_int

    year_blocks = []
    for year_name in year_names:
        year_start, year_end = get_school_year_dates(year_name)
        is_first_year = year_name == first_year_name
        is_current = year_name == current_year_name
        is_next = year_name == format_school_year(next_year_int)

        signups_in_year = [s for s in all_signups if year_start <= s.course.start_date <= year_end]
        total_signups = len(signups_in_year)

        if is_first_year:
            free_total = school.BASE_SEATS
            free_used = min(total_signups, free_total)
            forankringsplads_in_year = 0
            purchased = max(0, total_signups - free_total)
        else:
            free_total = 0
            free_used = 0
            forankringsplads_in_year = 1 if forankringsplads_year == year_name else 0
            purchased = total_signups - forankringsplads_in_year

        seats_price = calculate_seat_price(purchased)

        # Membership price
        if is_first_year:
            membership_price = 0
        else:
            year_start_int = parse_school_year(year_name)
            show_from = date(year_start_int, 6, 2)
            if today >= show_from:
                membership_price = MEMBERSHIP_PRICE
            else:
                membership_price = None  # not yet shown

        # Year activation: has published courses, or has signups already
        has_published = Course.objects.filter(
            start_date__gte=year_start,
            start_date__lte=year_end,
            is_published=True,
        ).exists()
        is_active = has_published or total_signups > 0
        is_greyed = is_next and not is_active

        year_blocks.append(
            {
                "year_name": year_name,
                "is_first_year": is_first_year,
                "is_current": is_current,
                "is_next": is_next,
                "is_active": is_active,
                "is_greyed": is_greyed,
                "is_collapsed": not is_current,
                "membership_price": membership_price,
                "total_signups": total_signups,
                "free_seats_total": free_total,
                "free_seats_used": free_used,
                "forankringsplads_in_year": forankringsplads_in_year,
                "purchased_seats": purchased,
                "seats_price": seats_price,
            }
        )

    forankringsplads_data = {
        "is_applicable": is_continuation,
        "used": 1 if forankringsplads_used else 0,
        "total": 1,
        "valid_until_year": FORANKRINGSPLADS_VALID_UNTIL,
        "is_expanded": not forankringsplads_used,
    }

    return {
        "years": year_blocks,
        "forankringsplads": forankringsplads_data,
    }
