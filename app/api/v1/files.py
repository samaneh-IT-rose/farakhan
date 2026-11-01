"""Secure admin file download.

The file must belong to the submission referenced in the URL, otherwise 404.
Content type and a safe filename are set in headers; path traversal is
impossible because content lives in the database, not on disk.
"""
from urllib.parse import quote

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.api.deps import get_current_admin, get_db_session
from app.core.errors import AppError
from app.repositories.submission_repository import get_file_row_for_download

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])


def _content_disposition(original_name: str, file_id: int) -> str:
    # ASCII fallback plus RFC 5987 encoded UTF-8 name (supports Persian names).
    ascii_fallback = f"file-{file_id}"
    encoded = quote(original_name, safe="")
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded}"


@router.get("/submissions/{submission_id}/files/{file_id}")
async def download_submission_file(
    submission_id: int,
    file_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    row = await get_file_row_for_download(session, submission_id, file_id)
    if row is None:
        raise AppError(status_code=404, message="فایل مورد نظر یافت نشد.")
    field_key, original_name, mime_type, content = row
    return Response(
        content=content,
        media_type=mime_type,
        headers={
            "Content-Disposition": _content_disposition(original_name, file_id),
            "X-File-Field": field_key,
            "Cache-Control": "no-store",
        },
    )
