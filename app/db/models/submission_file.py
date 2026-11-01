"""Submission file model: binary content stored in PostgreSQL BYTEA.

`content` is a deferred column so listing submissions never pulls file bytes.
Public direct access to files does not exist; downloads happen only through
the authorized admin endpoint.
"""
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

# BIGINT primary keys do not autoincrement on SQLite; tests run on SQLite.
BigIntPK = BigInteger().with_variant(Integer, "sqlite")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SubmissionFile(Base):
    __tablename__ = "submission_files"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("submissions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    field_key: Mapped[str] = mapped_column(String(64), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, deferred=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )

    submission: Mapped["Submission"] = relationship(  # type: ignore[name-defined]
        back_populates="files"
    )
