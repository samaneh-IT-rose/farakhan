"""Jalali (Solar Hijri) date parsing/formatting based on the jdatetime library.

Accepted input format: YYYY/MM/DD (also accepts "-" as separator and
Persian/Arabic digits). Future dates and implausible years are rejected.
"""
from datetime import date

import jdatetime

from app.utils.persian_digits import to_english_digits

MIN_JALALI_YEAR = 1250
MAX_JALALI_YEAR = 1500


def parse_jalali_date(value: str | None) -> jdatetime.date | None:
    """Parse a Jalali date string; return None when invalid."""
    if not value:
        return None
    normalized = to_english_digits(str(value)).strip().replace("-", "/")
    parts = normalized.split("/")
    if len(parts) != 3:
        return None
    try:
        year, month, day = (int(part) for part in parts)
    except ValueError:
        return None
    try:
        return jdatetime.date(year, month, day)
    except ValueError:
        return None


def is_plausible_jalali_date(value: jdatetime.date) -> bool:
    return MIN_JALALI_YEAR <= value.year <= MAX_JALALI_YEAR


def is_future_jalali_date(value: jdatetime.date) -> bool:
    return value > jdatetime.date.today()


def to_gregorian_date(jalali_date: jdatetime.date) -> date:
    return jalali_date.togregorian()


def from_gregorian_date(gregorian_date: date) -> jdatetime.date:
    return jdatetime.date.fromgregorian(date=gregorian_date)


def format_jalali(gregorian_date: date) -> str:
    """Format a Gregorian date as YYYY/MM/DD in the Jalali calendar."""
    return from_gregorian_date(gregorian_date).strftime("%Y/%m/%d")
