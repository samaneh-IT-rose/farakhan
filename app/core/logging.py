"""Logging configuration.

Security rule: request bodies, national codes, phone numbers, file contents and
secrets are NEVER logged. Only method, path, status code, duration and the
correlation request id are logged.
"""
import logging


def configure_logging(level: str = "INFO") -> None:
    log_level = getattr(logging, str(level).upper(), logging.INFO)
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
    logging.getLogger().setLevel(log_level)
    # Reduce noisy third-party loggers
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
