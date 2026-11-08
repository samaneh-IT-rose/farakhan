"""In-memory Idempotency-Key store for the public submission endpoint.

When a client sends an `Idempotency-Key` header with POST /api/v1/submissions,
the first successful response is cached for TTL seconds and replayed for
retries with the same key, preventing accidental duplicate submissions.

Single-instance only (documented). The store never contains personal data
beyond the tracking code response body.
"""
import time


class IdempotencyStore:
    def __init__(self, ttl_seconds: int = 24 * 60 * 60) -> None:
        self.ttl_seconds = ttl_seconds
        self._data: dict[str, tuple[float, dict]] = {}

    def get(self, key: str) -> dict | None:
        record = self._data.get(key)
        if record is None:
            return None
        created_at, body = record
        if time.time() - created_at > self.ttl_seconds:
            self._data.pop(key, None)
            return None
        return body

    def set(self, key: str, body: dict) -> None:
        if not key:
            return
        if len(self._data) > 10000:
            self._data.clear()
        self._data[key] = (time.time(), body)

    def clear(self) -> None:
        """Used by the test suite only."""
        self._data.clear()


idempotency_store = IdempotencyStore()
