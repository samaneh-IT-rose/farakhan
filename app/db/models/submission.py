"""Submission model: one row per submitted form.

- `national_code` is stored as String(10) and indexed (NOT unique: multiple
  submissions per national code are allowed until the product owner decides
  otherwise - open decision #14).
- `tracking_code` is unique + indexed and contains no personal data.
- Province/county names are stored as a snapshot at submission time.
"""
from datetime import date, datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

# BIGINT primary keys do not autoincrement on SQLite; tests use SQLite.
BigIntPK = BigInteger().with_variant(Integer, "sqlite")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    tracking_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)

    # Identity
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    national_code: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)
    birth_date_jalali: Mapped[str | None] = mapped_column(String(10), nullable=True)
    birth_date_gregorian: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Military status (only meaningful for male applicants)
    military_status: Mapped[str | None] = mapped_column(String(40), nullable=True)

    # Education
    education_degree: Mapped[str | None] = mapped_column(String(30), nullable=True)
    education_field: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Professional license
    license_status: Mapped[str] = mapped_column(String(20), nullable=False)
    license_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    license_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Center
    center_ownership: Mapped[str] = mapped_column(String(20), nullable=False)
    province_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("locations.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    county_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("locations.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    province_name: Mapped[str] = mapped_column(String(100), nullable=False)
    county_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Contact / address
    phone: Mapped[str | None] = mapped_column(String(15), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mobile_number: Mapped[str | None] = mapped_column(String(15), nullable=True)

    # Center capacity counters (>= 0)
    individual_rooms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    group_rooms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    child_rooms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    counselors_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Facility flags
    has_waiting_space: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    accepts_company_pattern: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_accessibility: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Terms acceptance (timestamp set by the server, not the client)
    terms_accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, onupdate=_utc_now
    )

    files: Mapped[list["SubmissionFile"]] = relationship(  # type: ignore[name-defined]
        back_populates="submission",
        cascade="all, delete-orphan",
        lazy="selectin",
        passive_deletes=True,
    )
