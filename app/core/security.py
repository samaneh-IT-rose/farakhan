"""Admin authentication: JWT issuing/verification and credential check.

Admin credentials come from environment variables (ADMIN_USERNAME /
ADMIN_PASSWORD) and are never stored in code or Git. For a single-admin
deployment this is the documented default (open decision #10); the token
machinery is ready for a multi-user upgrade later.
"""
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.core.config import Settings


def verify_admin_credentials(username: str, password: str, settings: Settings) -> bool:
    """Constant-time comparison of admin credentials against configured values."""
    ok_user = hmac.compare_digest(
        (username or "").encode("utf-8"), settings.ADMIN_USERNAME.encode("utf-8")
    )
    ok_pass = hmac.compare_digest(
        (password or "").encode("utf-8"), settings.ADMIN_PASSWORD.encode("utf-8")
    )
    return ok_user and ok_pass


def create_access_token(username: str, settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": username,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
        "scope": "admin",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str, settings: Settings) -> str | None:
    """Return the admin username for a valid token, otherwise None."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError:
        return None
    if payload.get("scope") != "admin":
        return None
    sub = payload.get("sub")
    return sub if isinstance(sub, str) else None
