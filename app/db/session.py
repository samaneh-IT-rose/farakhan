"""Async engine and session factory."""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings

settings = get_settings()

_engine_kwargs: dict = {"echo": False, "pool_pre_ping": True}

if settings.DATABASE_URL.startswith("sqlite"):
    # For in-memory SQLite (used by the test suite) all connections must share the same DB.
    if ":memory:" in settings.DATABASE_URL or settings.DATABASE_URL.rstrip("/") == "sqlite+aiosqlite://":
        _engine_kwargs["poolclass"] = StaticPool
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)


async def get_session() -> AsyncSession:
    """FastAPI dependency yielding an async session (transaction is owned by the service layer)."""
    async with SessionLocal() as session:
        yield session
