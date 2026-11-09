"""Application settings loaded from environment variables / .env file.

All business-rule knobs are centralized here so the product owner can change
defaults without touching code (see docs/open-decisions.md).
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # --- Application ---
    APP_ENV: str = "dev"  # dev | test | production
    PROJECT_NAME: str = "Farakhan Cooperation Form API"
    LOG_LEVEL: str = "INFO"
    TIMEZONE: str = "Asia/Tehran"

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://farakhan:farakhan_change_me@postgres:5432/farakhan"

    # --- Security ---
    SECRET_KEY: str = "change-me-to-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 240
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "ChangeMe@12345"
    CORS_ORIGINS: str = ""  # comma separated, e.g. https://form.example.com
    ALLOWED_FRAME_ANCESTORS: str = ""  # comma separated domains allowed to iframe /docs

    # --- Upload limits ---
    MAX_FILE_SIZE_BYTES: int = 5 * 1024 * 1024
    MAX_REQUEST_SIZE_BYTES: int = 30 * 1024 * 1024

    # --- Rate limiting (per client IP) ---
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_SUBMIT_PER_MINUTE: int = 10
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 5
    TRUST_X_FORWARDED_FOR: bool = False  # enable ONLY behind a trusted reverse proxy

    # --- Reports ---
    EXPORT_MAX_ROWS: int = 10000

    # --- Business rules (defaults documented in docs/open-decisions.md) ---
    MIN_AGE_YEARS: int = 0  # 0 = disabled, needs product-owner confirmation
    MAX_COUNTER_VALUE: int = 0  # 0 = no upper limit, needs product-owner confirmation
    REQUIRE_MILITARY_STATUS_FOR_MALE: bool = True
    REQUIRE_MILITARY_CARD_FOR_MALE: bool = False
    REQUIRE_LICENSE_DESCRIPTION: bool = False
    REQUIRE_PROPERTY_DOCUMENTS: bool = False
    # فیلدهای فایل اجباری (خواستهٔ مدیر سامانه): تصویر کارت ملی و تصویر مدرک تحصیلی
    REQUIRED_FILE_FIELDS: str = "national_id_card,degree_document"

    @property
    def cors_origins_list(self) -> list[str]:
        return _split_csv(self.CORS_ORIGINS)

    @property
    def allowed_frame_ancestors_list(self) -> list[str]:
        return _split_csv(self.ALLOWED_FRAME_ANCESTORS)

    @property
    def required_file_fields_list(self) -> list[str]:
        return _split_csv(self.REQUIRED_FILE_FIELDS)

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.strip().lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
