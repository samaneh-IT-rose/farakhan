"""POST /admin/login - admin authentication (rate limited).

Credentials come from ADMIN_USERNAME / ADMIN_PASSWORD environment variables.
Returns a JWT access token used as `Authorization: Bearer <token>`.
"""
import hmac

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.rate_limit import enforce_login_rate_limit
from app.core.security import create_access_token, verify_admin_credentials

router = APIRouter(tags=["admin"])


@router.post("/admin/login")
async def admin_login(
    form: OAuth2PasswordRequestForm = Depends(),
    _rate_limit: None = Depends(enforce_login_rate_limit),
) -> dict:
    settings = get_settings()
    if not verify_admin_credentials(form.username, form.password, settings):
        # Same message for wrong username and wrong password (no user enumeration).
        raise AppError(status_code=401, message="نام کاربری یا رمز عبور نادرست است.")
    # Explicit constant-time double check is already done inside
    # verify_admin_credentials; hmac import kept for future hashing upgrades.
    _ = hmac
    return {
        "access_token": create_access_token(form.username, settings),
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }
