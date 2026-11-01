"""Seed Iranian provinces/counties into the locations table (idempotent).

Run AFTER migrations:

    python -m app.db.seed_locations
or inside Docker:

    docker compose exec api python -m app.db.seed_locations

Data source: github.com/sajaddp/list-of-cities-in-Iran
(based on Statistical Center of Iran) - see docs/open-decisions.md item 8.
"""
import asyncio
import json
import logging
from pathlib import Path

from sqlalchemy import select

from app.db.models.location import LEVEL_COUNTY, LEVEL_PROVINCE, ROOT_PARENT_ID, Location
from app.db.session import SessionLocal

logger = logging.getLogger("farakhan.seed")

DATA_FILE = Path(__file__).parent / "seed_data" / "iran_locations.json"


async def _get_or_add_location(
    session, cache: dict[tuple[str, int, str], int], level: str, parent_id: int, name: str
) -> int:
    key = (level, parent_id, name)
    if key in cache:
        return cache[key]
    location_id = (
        await session.execute(
            select(Location.id).where(
                Location.level == level,
                Location.parent_id == parent_id,
                Location.name == name,
            )
        )
    ).scalar_one_or_none()
    if location_id is None:
        location = Location(name=name, level=level, parent_id=parent_id)
        session.add(location)
        await session.flush()  # assign the id inside the same transaction
        location_id = location.id
    cache[key] = location_id
    return location_id


async def seed() -> None:
    if not DATA_FILE.exists():
        logger.error("Seed data file not found: %s", DATA_FILE)
        raise SystemExit(1)

    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    cache: dict[tuple[str, int, str], int] = {}
    added_provinces = 0
    added_counties = 0

    async with SessionLocal() as session:
        async with session.begin():
            existing_ids = set(
                (await session.execute(select(Location.id))).scalars().all()
            )
            for province in data["provinces"]:
                province_name = province["name"].strip()
                province_id = await _get_or_add_location(
                    session, cache, LEVEL_PROVINCE, ROOT_PARENT_ID, province_name
                )
                if province_id not in existing_ids:
                    added_provinces += 1
                for county_name in province["counties"]:
                    county_id = await _get_or_add_location(
                        session, cache, LEVEL_COUNTY, province_id, county_name.strip()
                    )
                    if county_id not in existing_ids:
                        added_counties += 1
                        existing_ids.add(county_id)

            provinces_total = len(
                (await session.execute(select(Location).where(Location.level == LEVEL_PROVINCE))).scalars().all()
            )
            counties_total = len(
                (await session.execute(select(Location).where(Location.level == LEVEL_COUNTY))).scalars().all()
            )

    logger.info(
        "Location seed finished: new_provinces=%d | new_counties=%d | total_provinces=%d | total_counties=%d",
        added_provinces,
        added_counties,
        provinces_total,
        counties_total,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    asyncio.run(seed())


if __name__ == "__main__":
    main()
