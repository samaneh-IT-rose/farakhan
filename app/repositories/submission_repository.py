"""Repository helpers for Submission rows."""
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.submission import Submission
from app.db.models.submission_file import SubmissionFile


def _filter_conditions(
    *,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    province_id: int | None = None,
    tracking_code: str | None = None,
    national_code: str | None = None,
) -> list:
    conditions = []
    if created_from is not None:
        conditions.append(Submission.created_at >= created_from)
    if created_to is not None:
        conditions.append(Submission.created_at < created_to)
    if province_id is not None:
        conditions.append(Submission.province_id == province_id)
    if tracking_code:
        conditions.append(Submission.tracking_code == tracking_code.strip())
    if national_code:
        conditions.append(Submission.national_code == national_code.strip())
    return conditions


async def list_submissions(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    province_id: int | None = None,
    tracking_code: str | None = None,
    national_code: str | None = None,
) -> tuple[list[Submission], int]:
    """Paginated list; file binaries are never loaded (content is deferred)."""
    conditions = _filter_conditions(
        created_from=created_from,
        created_to=created_to,
        province_id=province_id,
        tracking_code=tracking_code,
        national_code=national_code,
    )
    total = await session.scalar(select(func.count()).select_from(Submission).where(*conditions))
    stmt = (
        select(Submission)
        .options(selectinload(Submission.files))
        .where(*conditions)
        .order_by(Submission.created_at.desc(), Submission.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await session.execute(stmt)).scalars().unique().all()
    return list(rows), int(total or 0)


async def get_submission(session: AsyncSession, submission_id: int) -> Submission | None:
    result = await session.execute(
        select(Submission)
        .options(selectinload(Submission.files))
        .where(Submission.id == submission_id)
    )
    return result.scalar_one_or_none()


async def get_file_row_for_download(
    session: AsyncSession, submission_id: int, file_id: int
):
    """Return (field_key, original_name, mime_type, content) for an authorized download."""
    result = await session.execute(
        select(
            SubmissionFile.field_key,
            SubmissionFile.original_name,
            SubmissionFile.mime_type,
            SubmissionFile.content,
        ).where(
            SubmissionFile.id == file_id,
            SubmissionFile.submission_id == submission_id,
        )
    )
    return result.first()
