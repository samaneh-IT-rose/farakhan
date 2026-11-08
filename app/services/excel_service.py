"""Excel (xlsx) export for admin reports.

- Text values are sanitized against formula injection (=, +, -, @ prefixes).
- File binaries are NOT exported; only attachment names/metadata.
- Row count is capped by EXPORT_MAX_ROWS.
- First column is the unique registry ID (شناسه) of each submission.
"""
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.core.constants import (
    CENTER_OWNERSHIP_OPTIONS,
    EDUCATION_DEGREE_LABELS,
    EXCEL_DANGEROUS_PREFIXES,
    FILE_FIELD_KEYS,
    GENDER_OPTIONS,
    LICENSE_STATUS_OPTIONS,
    MILITARY_STATUS_OPTIONS,
)
from app.db.models.submission import Submission
from app.utils.jalali_date import format_jalali

HEADER_ROW = [
    "شناسه", "کد پیگیری", "نام", "نام خانوادگی", "کد ملی", "جنسیت", "تاریخ تولد",
    "وضعیت سربازی", "مدرک تحصیلی", "رشته تحصیلی / توضیحات مدرک", "وضعیت پروانه",
    "توضیحات پروانه", "مالکیت مرکز", "استان", "شهرستان", "تلفن ثابت",
    "کدپستی", "نشانی", "اتاق فردی", "اتاق گروهی", "اتاق کودک",
    "تعداد مشاوران", "فضای انتظار", "پذیرش الگوی شرکت", "سهولت دسترسی",
    "شماره همراه", "پیوست‌ها", "تاریخ ثبت",
]

COLUMN_WIDTHS = [8, 16, 14, 16, 14, 8, 12, 16, 14, 20, 16, 24, 12, 12, 14, 14, 12, 30, 9, 9, 9, 12, 10, 14, 11, 14, 34, 12]


def sanitize_excel_cell(value) -> object:
    """Neutralize formula injection for text cells."""
    if isinstance(value, str) and value[:1] in EXCEL_DANGEROUS_PREFIXES:
        return "'" + value
    return value


def _label(options: dict[str, str], value: str | None) -> str:
    if value is None:
        return ""
    return options.get(value, value)


def _bool_label(value: bool) -> str:
    return "دارد" if value else "ندارد"


def _attachments_label(submission: Submission) -> str:
    parts = []
    for file_row in submission.files:
        label = FILE_FIELD_KEYS.get(file_row.field_key, file_row.field_key)
        parts.append(f"{label}: {file_row.original_name}")
    return " | ".join(parts)


def build_export_workbook(submissions: list[Submission]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "فرم‌های فراخوان"

    bold = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="1F7A5C")
    for column, title in enumerate(HEADER_ROW, start=1):
        cell = sheet.cell(row=1, column=column, value=title)
        cell.font = bold
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="right")
        sheet.column_dimensions[get_column_letter(column)].width = COLUMN_WIDTHS[column - 1]
    sheet.freeze_panes = "A2"

    for index, submission in enumerate(submissions, start=2):
        created_jalali = (
            format_jalali(submission.created_at.date()) if submission.created_at else ""
        )
        education_header_value = (
            submission.education_field
            if submission.education_degree == "other"
            else submission.education_field or ""
        )
        values = [
            submission.id,
            submission.tracking_code,
            submission.first_name,
            submission.last_name,
            submission.national_code,
            _label(GENDER_OPTIONS, submission.gender),
            submission.birth_date_jalali or "",
            _label(MILITARY_STATUS_OPTIONS, submission.military_status),
            _label(EDUCATION_DEGREE_LABELS, submission.education_degree),
            education_header_value or "",
            _label(LICENSE_STATUS_OPTIONS, submission.license_status),
            submission.license_description or "",
            _label(CENTER_OWNERSHIP_OPTIONS, submission.center_ownership),
            submission.province_name,
            submission.county_name,
            submission.phone or "",
            submission.postal_code or "",
            submission.address or "",
            submission.individual_rooms,
            submission.group_rooms,
            submission.child_rooms,
            submission.counselors_count,
            _bool_label(submission.has_waiting_space),
            "می‌پذیرد" if submission.accepts_company_pattern else "نمی‌پذیرد",
            _bool_label(submission.has_accessibility),
            submission.mobile_number,
            _attachments_label(submission),
            created_jalali,
        ]
        for column, value in enumerate(values, start=1):
            sheet.cell(row=index, column=column, value=sanitize_excel_cell(value))
        sheet.cell(row=index, column=2).alignment = Alignment(horizontal="right")

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
