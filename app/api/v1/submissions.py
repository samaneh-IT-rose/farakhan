"""POST /submissions - public form submission (multipart/form-data).

Request layout:
    payload: JSON string matching SubmissionCreate (see README for the schema)
    <file_field_key>: binary file parts, each named after its field key
        (military_card, national_id_card, degree_document, professional_license,
         center_activity_license, center_permit, property_documents)

- Rate limited per client IP (configurable).
- Supports the optional Idempotency-Key header to make retries safe.
- Form data and all files are stored in ONE transaction.
"""
import json

from fastapi import APIRouter, Depends, Request
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.formparsers import MultiPartException

from app.api.deps import get_db_session
from app.core.errors import AppError, AppValidationError, format_validation_errors
from app.core.idempotency import idempotency_store
from app.core.rate_limit import enforce_submit_rate_limit
from app.schemas.submission import SubmissionCreate
from app.services.submission_service import create_submission

router = APIRouter(tags=["submissions"])


async def _parse_multipart(request: Request) -> tuple[str, list]:
    try:
        form = await request.form()
    except MultiPartException as exc:
        raise AppError(status_code=400, message="قالب درخواست multipart نامعتبر است.") from exc

    payload_part = form.get("payload")
    if payload_part is None:
        raise AppValidationError(errors={"payload": "بخش payload الزامی است."})

    if not isinstance(payload_part, str):
        content = await payload_part.read()
        payload_part = content.decode("utf-8", errors="replace")

    uploads: list[tuple[str, object]] = []
    for key, value in form.multi_items():
        if key == "payload":
            continue
        if hasattr(value, "read"):  # UploadFile
            uploads.append((key, value))
    return payload_part, uploads


@router.post("/submissions", status_code=201)
async def submit_form(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    _rate_limit: None = Depends(enforce_submit_rate_limit),
) -> dict:
    idempotency_key = request.headers.get("Idempotency-Key")
    if idempotency_key:
        cached = idempotency_store.get(idempotency_key)
        if cached is not None:
            return cached

    payload_raw, uploads = await _parse_multipart(request)

    try:
        data = SubmissionCreate.model_validate_json(payload_raw)
    except ValidationError as exc:
        errors = format_validation_errors(exc.errors())
        # JSON-level errors have no field location; attribute them to the payload part.
        errors = {("payload" if key == "non_field_errors" else key): msg for key, msg in errors.items()}
        raise AppValidationError(errors=errors) from exc
    except ValueError as exc:
        raise AppValidationError(errors={"payload": "قالب JSON بخش payload نامعتبر است."}) from exc

    submission = await create_submission(session, data, uploads)  # type: ignore[arg-type]

    body = {
        "success": True,
        "tracking_code": submission.tracking_code,
        "message": "اطلاعات با موفقیت ثبت شد.",
    }
    if idempotency_key:
        idempotency_store.set(idempotency_key, body)
    return body
