"""Small, shared date-range helpers used by several rule modules."""

from datetime import date


def overlaps_exclusive(start_a: date, end_a: date, start_b: date, end_b: date) -> bool:
    """True if two windows share any day, treating a same-day handover
    (one ends the day the other starts) as NOT a conflict."""
    return start_a < end_b and start_b < end_a


def overlaps_inclusive(start_a: date, end_a: date, start_b: date, end_b: date) -> bool:
    """True if two windows share any day, including a shared boundary
    day - used when the question is "is anyone present on this day",
    not "is this a double-booking"."""
    return start_a <= end_b and start_b <= end_a
