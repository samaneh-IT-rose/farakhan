"""Iranian mobile and landline phone normalization/validation.

Normalization rules (documented in README):
- Persian/Arabic digits are converted to English.
- Separators (space, dash, parentheses) are removed.
- +98 / 0098 / 98 prefixes are converted to a leading 0.
- A 10-digit mobile missing the leading zero (9123456789) gets a leading 0.
- Mobile must match 09XXXXXXXXX; landline must match 0XXXXXXXXX (10-11 digits).
"""
import re

from app.utils.persian_digits import to_english_digits

_SEPARATORS_RE = re.compile(r"[\s\-().]")

MOBILE_RE = re.compile(r"^09\d{9}$")
# Landline: 0 + area code (starting with 1-8) + subscriber number = 11 digits.
# Mobile numbers (09...) are explicitly excluded by the second digit range.
LANDLINE_RE = re.compile(r"^0[1-8]\d{9}$")


def normalize_phone(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = _SEPARATORS_RE.sub("", to_english_digits(str(value))).strip()
    if not cleaned:
        return None
    if cleaned.startswith("+98"):
        cleaned = "0" + cleaned[3:]
    elif cleaned.startswith("0098"):
        cleaned = "0" + cleaned[4:]
    elif cleaned.startswith("98") and len(cleaned) == 12:
        cleaned = "0" + cleaned[2:]
    if len(cleaned) == 10 and cleaned.startswith("9"):
        cleaned = "0" + cleaned
    return cleaned


def is_valid_mobile(value: str | None) -> bool:
    value = normalize_phone(value)
    return bool(value and MOBILE_RE.match(value))


def is_valid_landline(value: str | None) -> bool:
    value = normalize_phone(value)
    return bool(value and LANDLINE_RE.match(value))
