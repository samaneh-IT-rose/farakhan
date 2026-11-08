"""File upload validation and storage.

Rules (from the PRD):
- Only PDF / JPG / JPEG / PNG, max 5 MB per file (configurable).
- Content type is verified by magic bytes, never by extension alone.
- Size is checked while reading so memory is not consumed unboundedly.
- Original names are sanitized and never used for filesystem paths or commands.
- Files are stored inside PostgreSQL (BYTEA) in the same transaction as the form.
"""
import re

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.constants import ALLOWED_FILE_TYPES, MAGIC_BYTES
from app.core.errors import AppValidationError
from app.utils.persian_digits import to_english_digits

_INVALID_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")
_MAX_ORIGINAL_NAME_LENGTH = 255


def sanitize_original_name(filename: str | None) -> str:
    """Strip any path parts and control characters; safe for headers and storage."""
    name = filename or ""
    name = name.replace("\\", "/").split("/")[-1]
    name = _INVALID_CHARS_RE.sub(" ", name).strip()
    if len(name) > _MAX_ORIGINAL_NAME_LENGTH:
        stem, dot, ext = name.rpartition(".")
        if dot and len(ext) < _MAX_ORIGINAL_NAME_LENGTH:
            name = stem[: _MAX_ORIGINAL_NAME_LENGTH - len(ext) - 1] + "." + ext
        else:
            name = name[:_MAX_ORIGINAL_NAME_LENGTH]
    return name or "file"


def detect_mime_type(data: bytes) -> str | None:
    for mime, signature in MAGIC_BYTES.items():
        if data.startswith(signature):
            return mime
    return None


def _field_error(field_key: str, message: str) -> AppValidationError:
    return AppValidationError(errors={f"files.{field_key}": message})


async def read_and_validate_upload(upload: UploadFile, field_key: str) -> tuple[dict, bytes]:
    """Validate one uploaded file and return (metadata, content)."""
    settings = get_settings()

    raw_name = upload.filename or ""
    extension = raw_name.rsplit(".", 1)[-1].lower() if "." in raw_name else ""
    if extension not in ALLOWED_FILE_TYPES:
        raise _field_error(
            field_key, "تنها فایل‌های PDF و تصویری (JPG، JPEG، PNG) پذیرفته می‌شود."
        )

    # Read at most MAX+1 bytes to detect oversize without consuming unbounded memory.
    content = await upload.read(settings.MAX_FILE_SIZE_BYTES + 1)
    if not content:
        raise _field_error(field_key, "فایل ارسالی خالی است.")
    if len(content) > settings.MAX_FILE_SIZE_BYTES:
        max_mb = round(settings.MAX_FILE_SIZE_BYTES / (1024 * 1024))
        raise _field_error(field_key, f"حجم فایل نباید بیش از {max_mb} مگابایت باشد.")

    detected_mime = detect_mime_type(content)
    expected_mime = ALLOWED_FILE_TYPES[extension]
    if detected_mime is None or detected_mime != expected_mime:
        raise _field_error(
            field_key, "محتوای فایل با پسوند اعلام‌شده همخوانی ندارد."
        )

    await upload.close()

    metadata = {
        "original_name": sanitize_original_name(raw_name),
        "mime_type": detected_mime,
        "size_bytes": len(content),
    }
    return metadata, content
