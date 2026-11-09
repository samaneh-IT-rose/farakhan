"""Centralized constants and option lists.

Every option shown to the user (gender, military status, education degree,
license status, center ownership, file field keys) lives here so the
`GET /api/v1/form/options` endpoint, validation, Excel export and print view
always stay consistent.
"""

# value -> Persian label
GENDER_OPTIONS: dict[str, str] = {
    "male": "مرد",
    "female": "زن",
}

# Open decision #1: exact military status options need product-owner confirmation
MILITARY_STATUS_OPTIONS: dict[str, str] = {
    "served": "پایان خدمت",
    "permanent_exemption": "معافیت دائم",
    "medical_exemption": "معافیت پزشکی",
    "temporary_exemption": "معافیت موقت / کسر خدمت",
}

# Open decision #2 (confirmed by product owner): only university degrees,
# starting from bachelor — no more «سایر» option.
EDUCATION_DEGREE_OPTIONS: dict[str, str] = {
    "bachelor": "کارشناسی",
    "master": "کارشناسی ارشد",
    "phd": "دکترا",
}

# برچسب‌های قدیمی برای ردیف‌هایی که پیش‌تر با گزینه‌های قدیمی ذخیره شده‌اند
EDUCATION_DEGREE_LABELS: dict[str, str] = {
    "diploma": "دیپلم",
    "associate": "کاردانی",
    "other": "سایر",
    **EDUCATION_DEGREE_OPTIONS,
}

# Open decision #3: nature of "پروانه فعالیت مرکز" needs product-owner confirmation
LICENSE_STATUS_OPTIONS: dict[str, str] = {
    "valid": "دارای پروانه معتبر",
    "in_progress": "در حال دریافت پروانه",
    "none": "فاقد پروانه",
}

CENTER_OWNERSHIP_OPTIONS: dict[str, str] = {
    "owned": "ملکی",
    "rented": "استیجاری",
    "other": "سایر",
}

# File upload field keys (part names in multipart/form-data)
# برچسب فایل‌های اجباری با واژهٔ «تصویر» شروع می‌شود تا با فیلد متن «مدرک
# تحصیلی» اشتباه نشود و پیام خطا دقیقاً نام همان فایل را بگوید.
FILE_FIELD_KEYS: dict[str, str] = {
    "military_card": "کارت پایان خدمت / معافیت",
    "national_id_card": "تصویر کارت ملی",
    "degree_document": "تصویر مدرک تحصیلی",
    "professional_license": "پروانه فعالیت / عضویت نظام",
    "center_activity_license": "مجوز فعالیت مرکز",
    "center_permit": "پروانه تأسیس مرکز",
    "property_documents": "اسناد مالکیت / اجاره‌نامه",
}

ALLOWED_FILE_TYPES: dict[str, str] = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
}

# Magic-byte signatures used to verify real content type (never trust extension alone)
MAGIC_BYTES: dict[str, bytes] = {
    "application/pdf": b"%PDF-",
    "image/jpeg": b"\xff\xd8\xff",
    "image/png": b"\x89PNG\r\n\x1a\n",
}

# Characters that must never start an Excel cell (formula injection protection)
EXCEL_DANGEROUS_PREFIXES = ("=", "+", "-", "@")
