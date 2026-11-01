"""Public location endpoints: provinces and their counties."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.errors import AppError
from app.db.models.location import LEVEL_COUNTY, Location
from app.repositories.location_repository import get_province, list_provinces

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("/provinces")
async def get_provinces(session: AsyncSession = Depends(get_db_session)) -> dict:
    provinces = await list_provinces(session)
    return {
        "success": True,
        "data": [{"id": province.id, "name": province.name} for province in provinces],
    }


@router.get("/provinces/{province_id}/counties")
async def get_counties(
    province_id: int, session: AsyncSession = Depends(get_db_session)
) -> dict:
    province = await get_province(session, province_id)
    if province is None:
        raise AppError(status_code=404, message="استان مورد نظر یافت نشد.")
    result = await session.execute(
        select(Location)
        .where(Location.level == LEVEL_COUNTY, Location.parent_id == province_id)
        .order_by(Location.name)
    )
    counties = result.scalars().all()
    return {
        "success": True,
        "data": [{"id": county.id, "name": county.name} for county in counties],
    }
