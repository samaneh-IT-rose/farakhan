"""Submission service: the heart of the business logic.

The form and ALL of its files are saved inside ONE transaction; on any failure
the whole thing rolls back, so no orphan files or partial data can remain.
"""
import logging
from datetime import date, datetime, timezone

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.constants import FILE_FIELD_KEYS
from app.core.errors import AppError, AppValidationError
from app.db.models.location import Location
from app.db.models.submission import Submission
from app.db.models.submission_file import SubmissionFile
from app.repositories.location_repository import get_county_of_province, get_province
from app.schemas.submission import SubmissionCreate
from app.services.file_service import read_and_validate_upload
from app.utils.jalali_date import parse_jalali_date, to_gregorian_date
from app.utils.tracking_code import generate_tracking_code

logger = logging.getLogger("farakhan.submissions")

DUPLICATE_TRACKING_ATTEMPTS = 5


def _location_errors(province: Location | None, county: Location | None) -> dict[str, str]:
    errors: dict[str, str] = {}
    if province is None:
        errors["province_id"] = "استان انتخاب‌شده معتبر نیست."
    if county is None:
        errors["county_id"] = "شهرستان انتخاب‌شده با استان همخوانی ندارد."
    return errors


async def _generate_unique_tracking_code(session: AsyncSession) -> str:
    for _ in range(DUPLICATE_TRACKING_ATTEMPTS):
        candidate = generate_tracking_code()
        exists = await session.scalar(
            select(func.count()).select_from(Submission).where(Submission.tracking_code == candidate)
        )
        if not exists:
            return candidate
    raise AppError(status_code=500, message="تولید کد پیگیری یکتا ممکن نشد. لطفاً دوباره تلاش کنید.")


async def create_submission(
    session: AsyncSession,
    data: SubmissionCreate,
    uploads: list[tuple[str, UploadFile]],
) -> Submission:
    """Validate everything and persist the submission + files in a single transaction."""
    settings = get_settings()

    try:
        async with session.begin():
            # 1) Locations must exist and the county must belong to the province.
            province = await get_province(session, data.province_id)
            county = (
                await get_county_of_province(session, data.county_id, data.province_id)
                if province
                else None
            )
            location_errors = _location_errors(province, county)
            if location_errors:
                raise AppValidationError(errors=location_errors)

            # 2) Read + validate every uploaded file (never trust client MIME).
            file_rows: list[SubmissionFile] = []
            seen_fields: set[str] = set()
            for field_key, upload in uploads:
                if field_key not in FILE_FIELD_KEYS:
                    raise AppValidationError(errors={f"files.{field_key}": "فیلد فایل نامعتبر است."})
                if field_key in seen_fields:
                    raise AppValidationError(
                        errors={
                            f"files.{field_key}": "برای هر فیلد فایل فقط یک فایل پذیرفته می‌شود."
                        }
                    )
                seen_fields.add(field_key)
                metadata, content = await read_and_validate_upload(upload, field_key)
                file_rows.append(
                    SubmissionFile(
                        field_key=field_key,
                        original_name=metadata["original_name"],
                        mime_type=metadata["mime_type"],
                        size_bytes=metadata["size_bytes"],
                        content=content,
                    )
                )

            # 3) Conditional/required file fields (centralized, product-owner configurable).
            required_fields = list(settings.required_file_fields_list)
            if data.gender == "male" and settings.REQUIRE_MILITARY_CARD_FOR_MALE:
                required_fields.append("military_card")
            if settings.REQUIRE_PROPERTY_DOCUMENTS:
                required_fields.append("property_documents")
            missing = [key for key in dict.fromkeys(required_fields) if key not in seen_fields]
            if missing:
                raise AppValidationError(
                    errors={
                        f"files.{key}": "بارگذاری این فایل الزامی است." for key in missing
                    }
                )

            # 4) Build the row; terms acceptance timestamp is set by the SERVER.
            birth_date = parse_jalali_date(data.birth_date)
            gregorian: date | None = to_gregorian_date(birth_date) if birth_date else None
            submission = Submission(
                tracking_code=await _generate_unique_tracking_code(session),
                first_name=data.first_name,
                last_name=data.last_name,
                national_code=data.national_code,
                gender=data.gender,
                birth_date_jalali=data.birth_date,
                birth_date_gregorian=gregorian,
                military_status=data.military_status,
                education_degree=data.education_degree,
                education_field=data.education_field,
                license_status=data.license_status,
                license_description=data.license_description,
                center_ownership=data.center_ownership,
                province_id=province.id,
                county_id=county.id,
                province_name=province.name,
                county_name=county.name,
                phone=data.phone,
                postal_code=data.postal_code,
                address=data.address,
                mobile_number=data.mobile_number,
                individual_rooms=data.individual_rooms,
                group_rooms=data.group_rooms,
                child_rooms=data.child_rooms,
                counselors_count=data.counselors_count,
                has_waiting_space=data.has_waiting_space,
                accepts_company_pattern=data.accepts_company_pattern,
                has_accessibility=data.has_accessibility,
                terms_accepted_at=datetime.now(timezone.utc),
            )
            submission.files = file_rows
            session.add(submission)
            await session.flush()
    except IntegrityError as exc:
        logger.warning("Integrity error while creating submission: %s", type(exc).__name__)
        raise AppError(
            status_code=409,
            message="خطای پردازش داده رخ داد. لطفاً دوباره تلاش کنید.",
        ) from exc

    return submission
