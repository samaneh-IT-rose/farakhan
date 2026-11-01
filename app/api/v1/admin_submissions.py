"""Admin submissions router: list, detail, Excel export and print data.

All routes require a valid admin JWT.
The national code is shown in full to the admin role; a masking helper is
provided for future limited roles (see mask_national_code in utils).
"""
import datetime as dt
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db_session
from app.core.config import get_settings
from app.core.errors import AppError, AppValidationError
from app.repositories.submission_repository import (
    get_submission,
    list_submissions,
)
from app.schemas.admin import PaginatedSubmissions, SubmissionDetail, SubmissionListItem
from app.schemas.submission import SubmissionCreate  # noqa: F401  (re-exported for docs)
from app.services.excel_service import build_export_workbook
from app.services.print_service import build_print_data
from app.utils.jalali_date import parse_jalali_date
from app.utils.national_code import normalize_national_code
from app.utils.persian_digits import to_english_digits

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])

DATE_FORMAT_MESSAGE = "تاریخ باید شمسی و به قالب YYYY/MM/DD باشد."


def _parse_filter_date(value: str | None, field: str, *, end_of_day: bool = False) -> datetime | None:
    if not value:
        return None
    jalali = parse_jalali_date(value)
    if jalali is None:
        raise AppValidationError(errors={field: DATE_FORMAT_MESSAGE})
    gregorian = jalali.togregorian()
    if end_of_day:
        next_day = gregorian + dt.timedelta(days=1)
        return datetime(next_day.year, next_day.month, next_day.day, tzinfo=timezone.utc)
    return datetime(gregorian.year, gregorian.month, gregorian.day, tzinfo=timezone.utc)


def _normalize_national_code_filter(value: str | None) -> str | None:
    if not value:
        return None
    return normalize_national_code(to_english_digits(value))


@router.get("/submissions")
async def list_submissions_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    date_from: str | None = Query(default=None, description="از تاریخ شمسی YYYY/MM/DD"),
    date_to: str | None = Query(default=None, description="تا تاریخ شمسی YYYY/MM/DD (شامل خود روز)"),
    province_id: int | None = Query(default=None, ge=1),
    tracking_code: str | None = Query(default=None),
    national_code: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await list_submissions(
        session,
        page=page,
        page_size=page_size,
        created_from=_parse_filter_date(date_from, "date_from"),
        created_to=_parse_filter_date(date_to, "date_to", end_of_day=True),
        province_id=province_id,
        tracking_code=tracking_code,
        national_code=_normalize_national_code_filter(national_code),
    )
    payload = PaginatedSubmissions(
        items=[SubmissionListItem.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )
    return {"success": True, "data": payload.model_dump(mode="json")}


@router.get("/submissions/export.xlsx")
async def export_submissions(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    province_id: int | None = Query(default=None, ge=1),
    tracking_code: str | None = Query(default=None),
    national_code: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    settings = get_settings()
    items, total = await list_submissions(
        session,
        page=1,
        page_size=settings.EXPORT_MAX_ROWS + 1,
        created_from=_parse_filter_date(date_from, "date_from"),
        created_to=_parse_filter_date(date_to, "date_to", end_of_day=True),
        province_id=province_id,
        tracking_code=tracking_code,
        national_code=_normalize_national_code_filter(national_code),
    )
    if total > settings.EXPORT_MAX_ROWS:
        raise AppError(
            status_code=400,
            message=f"تعداد ردیف‌ها بیش از حد مجاز ({settings.EXPORT_MAX_ROWS}) است. فیلترها را محدود کنید.",
        )
    content = build_export_workbook(items)
    today = dt.date.today().strftime("%Y%m%d")
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="submissions-export-{today}.xlsx"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/submissions/{submission_id}")
async def get_submission_detail(
    submission_id: int, session: AsyncSession = Depends(get_db_session)
) -> dict:
    submission = await get_submission(session, submission_id)
    if submission is None:
        raise AppError(status_code=404, message="فرم مورد نظر یافت نشد.")
    detail = SubmissionDetail.model_validate(submission)
    return {"success": True, "data": detail.model_dump(mode="json")}


@router.get("/submissions/{submission_id}/print")
async def get_submission_print(
    submission_id: int, session: AsyncSession = Depends(get_db_session)
) -> dict:
    submission = await get_submission(session, submission_id)
    if submission is None:
        raise AppError(status_code=404, message="فرم مورد نظر یافت نشد.")
    return {"success": True, "data": build_print_data(submission)}
