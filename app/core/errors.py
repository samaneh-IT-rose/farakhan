"""Unified error types and exception handlers.

Every error response in the API has the same shape:

    {"success": false, "message": "پیام فارسی", "errors": {"field": "پیام"}}

Internal errors never leak stack traces to the client.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("farakhan.errors")

NON_FIELD_KEY = "non_field_errors"

ERROR_TYPE_MESSAGES: dict[str, str] = {
    "missing": "این فیلد الزامی است.",
    "greater_than_equal": "مقدار نمی‌تواند منفی باشد.",
    "greater_than": "مقدار نامعتبر است.",
    "less_than_equal": "مقدار بیش از حد مجاز است.",
    "string_too_long": "طول متن بیش از حد مجاز است.",
    "string_too_short": "مقدار واردشده کوتاه‌تر از حد مجاز است.",
    "bool_parsing": "مقدار باید true یا false باشد.",
    "int_parsing": "مقدار باید عدد صحیح باشد.",
    "int_from_float": "مقدار باید عدد صحیح باشد.",
    "json_invalid": "قالب JSON نامعتبر است.",
    "literal_error": "مقدار انتخاب‌شده معتبر نیست.",
    "string_pattern_mismatch": "قالب مقدار واردشده صحیح نیست.",
}


class AppError(Exception):
    """Business error with an HTTP status, a Persian message and field errors."""

    def __init__(
        self,
        status_code: int = 400,
        message: str = "درخواست نامعتبر است.",
        errors: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.message = message
        self.errors = errors or {}
        super().__init__(message)


class AppValidationError(AppError):
    """Validation failure -> HTTP 422 with per-field Persian messages."""

    def __init__(
        self,
        errors: dict[str, str] | None = None,
        message: str = "اطلاعات ارسالی معتبر نیست.",
    ) -> None:
        super().__init__(status_code=422, message=message, errors=errors)


def _humanize(err: dict) -> str:
    msg = str(err.get("msg", ""))
    if msg.startswith("Value error, "):
        # Persian messages raised from pydantic validators
        return msg[len("Value error, "):]
    return ERROR_TYPE_MESSAGES.get(str(err.get("type", "")), "مقدار واردشده معتبر نیست.")


def validation_errors_to_dict(exc: RequestValidationError) -> dict[str, str]:
    """Convert pydantic validation errors into a flat {field: message} dict."""
    return format_validation_errors(exc.errors())


def format_validation_errors(errors_list: list[dict]) -> dict[str, str]:
    """Shared formatter used by both the FastAPI handler and manual parsing."""
    errors: dict[str, str] = {}
    for err in errors_list:
        loc = list(err.get("loc", []))
        if loc and loc[0] == "body":
            loc = loc[1:]
        key = ".".join(str(part) for part in loc) or NON_FIELD_KEY
        errors.setdefault(key, _humanize(err))
    return errors


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "message": "اطلاعات ارسالی معتبر نیست.",
                "errors": validation_errors_to_dict(exc),
            },
        )

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "message": exc.message, "errors": exc.errors},
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "خطای درخواست."
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "message": detail, "errors": {}},
        )

    @app.exception_handler(Exception)
    async def handle_unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Log full details server-side; return a generic message to the client.
        request_id = getattr(request.state, "request_id", "-")
        logger.exception("Unhandled server error [rid=%s]: %s", request_id, type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "خطای داخلی سرور رخ داد. لطفاً بعداً دوباره تلاش کنید.",
                "errors": {},
            },
        )
