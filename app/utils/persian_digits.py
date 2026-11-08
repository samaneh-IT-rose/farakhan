"""Convert Persian/Arabic digits to English digits.

Kept as strings everywhere: leading zeros of national codes and postal codes
must never be lost.
"""
_PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
_ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_ENGLISH_DIGITS = "0123456789"

_TRANSLATION = {ord(p): e for p, e in zip(_PERSIAN_DIGITS, _ENGLISH_DIGITS)}
_TRANSLATION.update({ord(a): e for a, e in zip(_ARABIC_DIGITS, _ENGLISH_DIGITS)})


def to_english_digits(value: str) -> str:
    """Translate Persian (۱۲۳) and Arabic (١٢٣) digits to English (123)."""
    if not value:
        return value
    return value.translate(_TRANSLATION)
