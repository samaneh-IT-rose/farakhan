"""GET /form/options - static, product-owner-approved form options."""
from fastapi import APIRouter

from app.core.config import get_settings
from app.core.constants import (
    ALLOWED_FILE_TYPES,
    CENTER_OWNERSHIP_OPTIONS,
    EDUCATION_DEGREE_OPTIONS,
    FILE_FIELD_KEYS,
    GENDER_OPTIONS,
    LICENSE_STATUS_OPTIONS,
    MILITARY_STATUS_OPTIONS,
)

router = APIRouter(tags=["form"])


def _options(mapping: dict[str, str]) -> list[dict[str, str]]:
    return [{"value": key, "label": label} for key, label in mapping.items()]


@router.get("/form/options")
async def get_form_options() -> dict:
    settings = get_settings()
    return {
        "success": True,
        "data": {
            "genders": _options(GENDER_OPTIONS),
            "military_status_options": _options(MILITARY_STATUS_OPTIONS),
            "education_degrees": _options(EDUCATION_DEGREE_OPTIONS),
            "license_status_options": _options(LICENSE_STATUS_OPTIONS),
            "center_ownership_options": _options(CENTER_OWNERSHIP_OPTIONS),
            "file_fields": [{"key": key, "label": label} for key, label in FILE_FIELD_KEYS.items()],
            "allowed_extensions": list(ALLOWED_FILE_TYPES.keys()),
            "max_file_size_bytes": settings.MAX_FILE_SIZE_BYTES,
            "max_request_size_bytes": settings.MAX_REQUEST_SIZE_BYTES,
            "max_counter_value": settings.MAX_COUNTER_VALUE if settings.MAX_COUNTER_VALUE > 0 else None,
            "required_file_fields": settings.required_file_fields_list,
        },
    }
