"""Location model: provinces and counties (شهرستان).

parent_id uses 0 as sentinel for provinces (top level) so that the unique
constraint (level, parent_id, name) works on both PostgreSQL and SQLite.
"""
from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base

LEVEL_PROVINCE = "province"
LEVEL_COUNTY = "county"
ROOT_PARENT_ID = 0


class Location(Base):
    __tablename__ = "locations"
    __table_args__ = (
        UniqueConstraint("level", "parent_id", "name", name="uq_locations_level_parent_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    level: Mapped[str] = mapped_column(String(10), nullable=False, default=LEVEL_PROVINCE)
    parent_id: Mapped[int] = mapped_column(Integer, nullable=False, default=ROOT_PARENT_ID, index=True)
