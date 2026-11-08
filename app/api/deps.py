"""Shared FastAPI dependencies (auth, DB session)."""
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.session import get_session

bearer_scheme = HTTPBearer(auto_error=False, description="توکن JWT مدیر")


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """Require a valid admin JWT; raise 401 otherwise."""
    if credentials is None or not credentials.credentials:
        raise AppError(status_code=401, message="برای دسترسی به این بخش باید وارد شوید.")
    settings = get_settings()
    username = decode_access_token(credentials.credentials, settings)
    if username is None:
        raise AppError(
            status_code=401,
            message="نشست شما منقضی یا نامعتبر است. لطفاً دوباره وارد شوید.",
        )
    return username


# Re-export so routers can use a single import path
get_db_session = get_session

__all__ = ["get_current_admin", "get_db_session", "AsyncSession"]
