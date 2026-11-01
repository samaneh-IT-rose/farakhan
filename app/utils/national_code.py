"""Iranian national code (کد ملی) validation.

Official algorithm: weighted sum of the first 9 digits, modulo 11, compared
with the 10th control digit. Codes with all-identical digits are invalid.
The code is handled strictly as a string to preserve leading zeros.
"""
from app.utils.persian_digits import to_english_digits


def normalize_national_code(value: str | None) -> str | None:
    if value is None:
        return None
    return to_english_digits(str(value)).strip()


def is_valid_national_code(code: str | None) -> bool:
    code = normalize_national_code(code) if code else None
    if not code or not code.isdigit() or len(code) != 10:
        return False
    if code == code[0] * 10:  # 0000000000, 1111111111, ... are invalid
        return False
    weighted_sum = sum(int(digit) * (10 - index) for index, digit in enumerate(code[:9]))
    remainder = weighted_sum % 11
    control = int(code[9])
    if remainder < 2:
        return control == remainder
    return control == 11 - remainder


def mask_national_code(code: str | None) -> str:
    """Show only the first 4 digits; for roles without full-visibility permission."""
    code = normalize_national_code(code) if code else ""
    if not code:
        return ""
    return code[:4] + "*" * max(len(code) - 4, 0)
