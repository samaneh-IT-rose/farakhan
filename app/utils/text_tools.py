"""Small text helpers: trimming and empty-to-None conversion."""
import re

_WHITESPACE_RE = re.compile(r"\s+")


def clean_text(value: str | None) -> str | None:
    """Strip surrounding whitespace, collapse inner runs, map empty to None."""
    if value is None:
        return None
    cleaned = _WHITESPACE_RE.sub(" ", str(value)).strip()
    return cleaned or None
