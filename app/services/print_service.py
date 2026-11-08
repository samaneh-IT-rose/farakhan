"""Print-friendly data builder for a single submission.

Returns structured, label-formatted JSON the frontend can render or convert to
PDF. File binaries are never embedded automatically (per PRD).
"""
from app.core.constants import (
    CENTER_OWNERSHIP_OPTIONS,
    EDUCATION_DEGREE_LABELS,
    FILE_FIELD_KEYS,
    GENDER_OPTIONS,
    LICENSE_STATUS_OPTIONS,
    MILITARY_STATUS_OPTIONS,
)
from app.db.models.submission import Submission
from app.utils.jalali_date import format_jalali


def _label(options: dict[str, str], value: str | None) -> str | None:
    if value is None:
        return None
    return options.get(value, value)


def _bool(value: bool) -> str:
    return "دارد" if value else "ندارد"


def build_print_data(submission: Submission) -> dict:
    created_at = submission.created_at
    education_label = (
        "توضیحات مدرک (سایر)"
        if submission.education_degree == "other"
        else "رشته تحصیلی"
    )
    fields = [
        {"label": "کد پیگیری", "value": submission.tracking_code},
        {"label": "نام و نام خانوادگی", "value": f"{submission.first_name} {submission.last_name}"},
        {"label": "کد ملی", "value": submission.national_code},
        {"label": "جنسیت", "value": _label(GENDER_OPTIONS, submission.gender)},
        {"label": "تاریخ تولد", "value": submission.birth_date_jalali or ""},
        {"label": "وضعیت سربازی", "value": _label(MILITARY_STATUS_OPTIONS, submission.military_status) or "—"},
        {"label": "مدرک تحصیلی", "value": _label(EDUCATION_DEGREE_LABELS, submission.education_degree) or "—"},
        {"label": education_label, "value": submission.education_field or "—"},
        {"label": "وضعیت پروانه", "value": _label(LICENSE_STATUS_OPTIONS, submission.license_status)},
        {"label": "توضیحات پروانه", "value": submission.license_description or "—"},
        {"label": "مالکیت مرکز", "value": _label(CENTER_OWNERSHIP_OPTIONS, submission.center_ownership)},
        {"label": "استان", "value": submission.province_name},
        {"label": "شهرستان", "value": submission.county_name},
        {"label": "تلفن ثابت", "value": submission.phone or "—"},
        {"label": "شماره همراه", "value": submission.mobile_number},
        {"label": "کدپستی", "value": submission.postal_code or "—"},
        {"label": "نشانی", "value": submission.address or "—"},
        {"label": "اتاق‌های مشاوره فردی", "value": submission.individual_rooms},
        {"label": "اتاق‌های مشاوره گروهی", "value": submission.group_rooms},
        {"label": "اتاق‌های مشاوره کودک", "value": submission.child_rooms},
        {"label": "تعداد مشاوران", "value": submission.counselors_count},
        {"label": "فضای انتظار", "value": _bool(submission.has_waiting_space)},
        {
            "label": "پذیرش الگوی شرکت",
            "value": "می‌پذیرد" if submission.accepts_company_pattern else "نمی‌پذیرد",
        },
        {"label": "سهولت دسترسی", "value": _bool(submission.has_accessibility)},
        {"label": "تاریخ ثبت فرم", "value": format_jalali(created_at.date()) if created_at else ""},
    ]
    files = [
        {
            "field_key": file_row.field_key,
            "label": FILE_FIELD_KEYS.get(file_row.field_key, file_row.field_key),
            "file_name": file_row.original_name,
            "size_bytes": file_row.size_bytes,
            "mime_type": file_row.mime_type,
        }
        for file_row in submission.files
    ]
    return {
        "submission_id": submission.id,
        "tracking_code": submission.tracking_code,
        "fields": fields,
        "files": files,
    }
