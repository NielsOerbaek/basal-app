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
    """Stub — implemented in Task 2."""
    return None
