"""In-memory sliding-window rate limiter for public endpoints.

Designed for single-instance deployments (documented limitation). For horizontal
scaling replace with a Redis-backed limiter; the interface stays the same.
"""
import asyncio
import time

from fastapi import Request

from app.core.config import Settings, get_settings
from app.core.errors import AppError


class SlidingWindowRateLimiter:
    def __init__(self, window_seconds: int = 60) -> None:
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    async def allow(self, key: str, limit: int) -> bool:
        if limit <= 0:
            return True
        now = time.monotonic()
        async with self._lock:
            bucket = [t for t in self._hits.get(key, []) if now - t < self.window_seconds]
            if len(bucket) >= limit:
                self._hits[key] = bucket
                return False
            bucket.append(now)
            self._hits[key] = bucket
            # Opportunistic cleanup of stale keys
            if len(self._hits) > 10000:
                cutoff = now - self.window_seconds
                self._hits = {k: v for k, v in self._hits.items() if v and v[-1] > cutoff}
            return True

    def clear(self) -> None:
        """Used by the test suite only."""
        self._hits.clear()


def client_ip(request: Request, trust_proxy: bool = False) -> str:
    if trust_proxy:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


submit_limiter = SlidingWindowRateLimiter()
login_limiter = SlidingWindowRateLimiter()


def _client_ip_from_settings(request: Request) -> str:
    settings: Settings = get_settings()
    return client_ip(request, trust_proxy=settings.TRUST_X_FORWARDED_FOR)


async def enforce_submit_rate_limit(request: Request) -> None:
    settings = get_settings()
    if not settings.RATE_LIMIT_ENABLED:
        return
    allowed = await submit_limiter.allow(
        _client_ip_from_settings(request), settings.RATE_LIMIT_SUBMIT_PER_MINUTE
    )
    if not allowed:
        raise AppError(
            status_code=429,
            message="تعداد درخواست‌های شما بیش از حد مجاز است. لطفاً کمی بعد دوباره تلاش کنید.",
        )


async def enforce_login_rate_limit(request: Request) -> None:
    settings = get_settings()
    if not settings.RATE_LIMIT_ENABLED:
        return
    allowed = await login_limiter.allow(
        _client_ip_from_settings(request), settings.RATE_LIMIT_LOGIN_PER_MINUTE
    )
    if not allowed:
        raise AppError(
            status_code=429,
            message="تعداد تلاش‌های ورود بیش از حد مجاز است. لطفاً کمی بعد دوباره تلاش کنید.",
        )
