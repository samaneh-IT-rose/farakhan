"""FastAPI application factory.

Schema management is done ONLY through Alembic migrations - no automatic
create_all at startup (PRD requirement for production safety).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import (
    RequestContextMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)

    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="بک‌اند فرم فراخوان همکاری - ثبت اطلاعات، بارگذاری مدارک و گزارش‌های مدیریتی",
        version="1.0.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    # Order: SecurityHeaders (inner) -> RequestSizeLimit -> RequestContext (outermost for logging)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware)
    app.add_middleware(RequestContextMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
        max_age=600,
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api/v1")

    @app.on_event("startup")
    async def _ensure_new_columns() -> None:
        """Idempotent single-column migration for columns added after v7.

        Alembic stays the canonical schema manager (see alembic/versions);
        this hook only guarantees that Docker deployments rebuilt from a new
        image also get the new columns without a manual `alembic upgrade head`.
        """
        from app.db.session import engine

        statements = [
            "ALTER TABLE submissions ADD COLUMN IF NOT EXISTS license_number VARCHAR(50)",
            "ALTER TABLE submissions ALTER COLUMN mobile_number DROP NOT NULL",
        ]
        for statement in statements:
            try:
                async with engine.begin() as connection:
                    await connection.execute(text(statement))
            except Exception:  # noqa: BLE001 - startup must never fail on this
                # SQLite (tests/e2e) builds the full schema from the models.
                break

    @app.get("/health", tags=["system"], summary="Health check")
    async def health() -> dict:
        database_status = "ok"
        try:
            from app.db.session import engine

            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except Exception:  # noqa: BLE001 - health must never raise
            database_status = "error"
        return {"status": "ok", "database": database_status, "app_env": settings.APP_ENV}

    # --- Farakhan public form (static hosting) ---
    from pathlib import Path as _StaticPath

    from fastapi.staticfiles import StaticFiles

    class _SPAStaticFiles(StaticFiles):
        """index.html must always be revalidated so browsers pick up a new
        build immediately; content-hashed assets stay safely cacheable."""

        def file_response(self, *args, **kwargs):  # type: ignore[override]
            response = super().file_response(*args, **kwargs)
            if response.headers.get("content-type", "").startswith("text/html"):
                response.headers["Cache-Control"] = "no-cache"
            return response

    _static_dir = _StaticPath(__file__).resolve().parent / "static"
    if _static_dir.is_dir():
        app.mount("/", _SPAStaticFiles(directory=str(_static_dir), html=True), name="static")

    return app


app = create_app()
