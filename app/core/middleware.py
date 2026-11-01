"""HTTP middlewares: correlation id + access log, security headers and request size limit."""
import logging
import time
import uuid

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings

logger = logging.getLogger("farakhan.access")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a correlation id (X-Request-ID) to every request and logs the outcome."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        duration_ms = (time.perf_counter() - started) * 1000
        # Only method/path/status are logged - never query strings or bodies.
        logger.info(
            "%s %s -> %s (%.1f ms) [rid=%s]",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds baseline security headers including CSP frame-ancestors for iframe embedding."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        settings = get_settings()
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        ancestors = "'self'" + "".join(f" {a}" for a in settings.allowed_frame_ancestors_list)
        response.headers.setdefault("Content-Security-Policy", f"frame-ancestors {ancestors}")
        if not settings.allowed_frame_ancestors_list:
            response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects requests whose Content-Length exceeds the configured limit (HTTP 413)."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()
        content_length = request.headers.get("content-length", "")
        if content_length.isdigit() and int(content_length) > settings.MAX_REQUEST_SIZE_BYTES:
            return JSONResponse(
                status_code=413,
                content={
                    "success": False,
                    "message": "حجم درخواست بیش از حد مجاز است.",
                    "errors": {},
                },
            )
        return await call_next(request)
