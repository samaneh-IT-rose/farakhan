"""Repository helpers for Location rows."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.location import LEVEL_COUNTY, LEVEL_PROVINCE, ROOT_PARENT_ID, Location
from app.utils.persian_text import persian_alpha_key


async def list_provinces(session: AsyncSession) -> list[Location]:
    """فهرست استان‌ها به ترتیب الفبای فارسی."""
    result = await session.execute(
        select(Location).where(Location.level == LEVEL_PROVINCE)
    )
    provinces = list(result.scalars().all())
    provinces.sort(key=lambda province: persian_alpha_key(province.name))
    return provinces


async def list_counties_of_province(
    session: AsyncSession, province_id: int
) -> list[Location]:
    """فهرست شهرستان‌های یک استان به ترتیب الفبای فارسی."""
    result = await session.execute(
        select(Location).where(
            Location.level == LEVEL_COUNTY, Location.parent_id == province_id
        )
    )
    counties = list(result.scalars().all())
    counties.sort(key=lambda county: persian_alpha_key(county.name))
    return counties


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
