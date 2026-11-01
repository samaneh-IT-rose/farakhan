"""Repository helpers for Location rows."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.location import LEVEL_COUNTY, LEVEL_PROVINCE, ROOT_PARENT_ID, Location


async def list_provinces(session: AsyncSession) -> list[Location]:
    result = await session.execute(
        select(Location).where(Location.level == LEVEL_PROVINCE).order_by(Location.id)
    )
    return list(result.scalars().all())


async def get_province(session: AsyncSession, province_id: int) -> Location | None:
    result = await session.execute(
        select(Location).where(
            Location.id == province_id,
            Location.level == LEVEL_PROVINCE,
            Location.parent_id == ROOT_PARENT_ID,
        )
    )
    return result.scalar_one_or_none()


async def get_county_of_province(
    session: AsyncSession, county_id: int, province_id: int
) -> Location | None:
    result = await session.execute(
        select(Location).where(
            Location.id == county_id,
            Location.level == LEVEL_COUNTY,
            Location.parent_id == province_id,
        )
    )
    return result.scalar_one_or_none()
