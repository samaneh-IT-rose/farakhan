"""Pydantic schema for creating a submission (public form payload).

All normalization happens in field validators (Persian digits, separators,
trimming); all business rules raise Persian error messages.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.config import get_settings
from app.utils.national_code import is_valid_national_code
from app.utils.phone import is_valid_landline, is_valid_mobile, normalize_phone
from app.utils.postal_code import is_valid_postal_code_format
from app.utils.jalali_date import (
    is_future_jalali_date,
    is_plausible_jalali_date,
    parse_jalali_date,
    to_gregorian_date,
)
from app.utils.persian_digits import to_english_digits
from app.utils.text_tools import clean_text

Gender = Literal["male", "female"]
MilitaryStatus = Literal["served", "permanent_exemption", "medical_exemption", "temporary_exemption"]
# فقط مدارک دانشگاهی از کارشناسی به بالا (خواستهٔ مدیر سامانه)
EducationDegree = Literal["bachelor", "master", "phd"]
LicenseStatus = Literal["valid", "in_progress", "none"]
CenterOwnership = Literal["owned", "rented", "other"]

BIRTH_DATE_MESSAGE = "تاریخ تولد باید تاریخ شمسی معتبر به قالب YYYY/MM/DD باشد."
FUTURE_DATE_MESSAGE = "تاریخ تولد نمی‌تواند در آینده باشد."
IMPLAUSIBLE_DATE_MESSAGE = "تاریخ تولد واردشده معقول نیست."
MOBILE_MESSAGE = "شماره همراه معتبر نیست. نمونه صحیح: 09123456789"
PHONE_MESSAGE = "شماره تلفن ثابت معتبر نیست. نمونه صحیح: 02112345678"
POSTAL_CODE_MESSAGE = "کدپستی باید ۱۰ رقم باشد."
NATIONAL_CODE_LENGTH_MESSAGE = "کد ملی باید ۱۰ رقم باشد."
NATIONAL_CODE_INVALID_MESSAGE = "کد ملی واردشده معتبر نیست."
TERMS_MESSAGE = "پذیرش قوانین و شرایط برای ثبت نهایی الزامی است."
EDUCATION_DEGREE_MESSAGE = "مدرک تحصیلی را انتخاب کنید."
EDUCATION_FIELD_MESSAGE = "رشته تحصیلی را وارد کنید."


class SubmissionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    # Identity
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    national_code: str = Field(min_length=1, max_length=20)
    gender: Gender
    birth_date: str = Field(min_length=8, max_length=10)

    # Military (conditional)
    military_status: MilitaryStatus | None = None

    # Education (هر دو فیلد الزامی‌اند)
    education_degree: EducationDegree
    education_field: str | None = Field(default=None, max_length=120)

    # License
    license_status: LicenseStatus
    license_description: str | None = Field(default=None, max_length=1000)

    # Center
    center_ownership: CenterOwnership
    province_id: int = Field(gt=0)
    county_id: int = Field(gt=0)

    # Contact / address
    phone: str | None = Field(default=None, max_length=20)
    postal_code: str | None = Field(default=None, max_length=15)
    address: str | None = Field(default=None, max_length=500)
    # Length/format is fully validated by the custom validator so the error
    # message is always the Persian one.
    mobile_number: str = Field(max_length=20)

    # Capacity counters
    individual_rooms: int = Field(ge=0)
    group_rooms: int = Field(ge=0)
    child_rooms: int = Field(ge=0)
    counselors_count: int = Field(ge=0)

    # Facility flags
    has_waiting_space: bool
    accepts_company_pattern: bool
    has_accessibility: bool

    # Terms
    terms_accepted: bool

    # ---------- normalizers ----------
    @field_validator("education_degree", mode="before")
    @classmethod
    def _require_education_degree(cls, value):
        # حتی اگر فرم قدیمی مقدار null بفرستد، پیام دقیق همان فیلد نمایش داده می‌شود.
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValueError(EDUCATION_DEGREE_MESSAGE)
        return value

    @field_validator("national_code", "birth_date", "postal_code", mode="before")
    @classmethod
    def _normalize_digits(cls, value):
        if value is None:
            return None
        return to_english_digits(str(value)).strip()

    @field_validator("first_name", "last_name", "education_field", "license_description", "address", mode="before")
    @classmethod
    def _clean_text(cls, value):
        return clean_text(value) if value is not None else None

    # ---------- per-field rules ----------
    @field_validator("national_code")
    @classmethod
    def _validate_national_code(cls, value: str) -> str:
        if len(value) != 10 or not value.isdigit():
            raise ValueError(NATIONAL_CODE_LENGTH_MESSAGE)
        if not is_valid_national_code(value):
            raise ValueError(NATIONAL_CODE_INVALID_MESSAGE)
        return value

    @field_validator("birth_date")
    @classmethod
    def _validate_birth_date(cls, value: str) -> str:
        jalali = parse_jalali_date(value)
        if jalali is None:
            raise ValueError(BIRTH_DATE_MESSAGE)
        if not is_plausible_jalali_date(jalali):
            raise ValueError(IMPLAUSIBLE_DATE_MESSAGE)
        if is_future_jalali_date(jalali):
            raise ValueError(FUTURE_DATE_MESSAGE)
        settings = get_settings()
        if settings.MIN_AGE_YEARS > 0:
            gregorian = to_gregorian_date(jalali)
            today = to_gregorian_date(jalali.__class__.today())
            age = today.year - gregorian.year - ((today.month, today.day) < (gregorian.month, gregorian.day))
            if age < settings.MIN_AGE_YEARS:
                raise ValueError(f"سن متقاضی باید حداقل {settings.MIN_AGE_YEARS} سال باشد.")
        return value

    @field_validator("postal_code")
    @classmethod
    def _validate_postal_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not is_valid_postal_code_format(value):
            raise ValueError(POSTAL_CODE_MESSAGE)
        return value

    @field_validator("mobile_number")
    @classmethod
    def _validate_mobile(cls, value: str) -> str:
        normalized = normalize_phone(value)
        if not normalized or not is_valid_mobile(normalized):
            raise ValueError(MOBILE_MESSAGE)
        return normalized

    @field_validator("education_field")
    @classmethod
    def _require_education_field(cls, value: str | None) -> str:
        # رشته تحصیلی برای همهٔ متقاضیان الزامی است.
        if not (value or "").strip():
            raise ValueError(EDUCATION_FIELD_MESSAGE)
        return value

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_phone(value)
        if not normalized or not is_valid_landline(normalized):
            raise ValueError(PHONE_MESSAGE)
        return normalized

    @field_validator("individual_rooms", "group_rooms", "child_rooms", "counselors_count")
    @classmethod
    def _validate_counter_upper_limit(cls, value: int) -> int:
        settings = get_settings()
        if settings.MAX_COUNTER_VALUE > 0 and value > settings.MAX_COUNTER_VALUE:
            raise ValueError(f"مقدار نمی‌تواند بیش از {settings.MAX_COUNTER_VALUE} باشد.")
        return value

    @field_validator("terms_accepted")
    @classmethod
    def _validate_terms(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError(TERMS_MESSAGE)
        return value

    # ---------- cross-field rules ----------
    @model_validator(mode="after")
    def _apply_conditional_rules(self) -> "SubmissionCreate":
        settings = get_settings()

        # Military data is only meaningful for male applicants.
        # Documented behavior (open decision #1): for female applicants the
        # military fields are silently nulled instead of rejected.
        if self.gender == "female":
            self.military_status = None
        elif self.gender == "male" and settings.REQUIRE_MILITARY_STATUS_FOR_MALE and not self.military_status:
            raise ValueError("وضعیت سربازی برای متقاضی مرد الزامی است.")

        # License consistency
        if self.license_status == "none":
            self.license_description = None
        elif settings.REQUIRE_LICENSE_DESCRIPTION and not self.license_description:
            raise ValueError("توضیحات مربوط به پروانه الزامی است.")

        return self
