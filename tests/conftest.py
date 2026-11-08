"""Shared pytest fixtures.

The test suite runs on in-memory SQLite (isolated from any real data) while the
production configuration targets PostgreSQL. Environment variables are set
BEFORE importing the application so cached settings pick them up.
"""
import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "admin-pass-123"
os.environ["RATE_LIMIT_SUBMIT_PER_MINUTE"] = "1000"
os.environ["RATE_LIMIT_LOGIN_PER_MINUTE"] = "1000"
os.environ["REQUIRED_FILE_FIELDS"] = ""
os.environ["MIN_AGE_YEARS"] = "0"
os.environ["MAX_COUNTER_VALUE"] = "0"
os.environ["APP_ENV"] = "test"

import json  # noqa: E402

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.idempotency import idempotency_store  # noqa: E402
from app.core.rate_limit import login_limiter, submit_limiter  # noqa: E402
from app.db.base_class import Base  # noqa: E402
from app.db.models.location import Location  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402

# Fixed test location ids (seeded fresh for every test)
PROVINCE_A_ID = 9001
COUNTY_A_ID = 9002
PROVINCE_B_ID = 9101
COUNTY_B_ID = 9102

MINIMAL_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
MINIMAL_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
MINIMAL_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32

ADMIN_LOGIN_BODY = {"username": "admin", "password": "admin-pass-123"}


def valid_national_code(base9: str = "123456789") -> str:
    """Compute the control digit for the first 9 digits -> a valid code."""
    weighted = sum(int(d) * (10 - i) for i, d in enumerate(base9))
    remainder = weighted % 11
    control = remainder if remainder < 2 else 11 - remainder
    return base9 + str(control)


def valid_payload(**overrides) -> dict:
    payload = {
        "first_name": "علی",
        "last_name": "رضایی",
        "national_code": valid_national_code("123456789"),  # 1234567891
        "gender": "male",
        "birth_date": "1370/05/10",
        "military_status": "served",
        "education_degree": "bachelor",
        "education_field": "روانشناسی",
        "license_status": "valid",
        "license_description": "پروانه معتبر نظام مشاوره",
        "center_ownership": "rented",
        "province_id": PROVINCE_A_ID,
        "county_id": COUNTY_A_ID,
        "phone": "02112345678",
        "postal_code": "1234567890",
        "address": "تهران، خیابان آزمون، پلاک ۱",
        "mobile_number": "09121234567",
        "individual_rooms": 2,
        "group_rooms": 1,
        "child_rooms": 0,
        "counselors_count": 3,
        "has_waiting_space": True,
        "accepts_company_pattern": True,
        "has_accessibility": False,
        "terms_accepted": True,
    }
    payload.update(overrides)
    return payload


@pytest.fixture(autouse=True)
async def database():
    """Fresh schema + known locations for every test."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        async with session.begin():
            session.add_all(
                [
                    Location(id=PROVINCE_A_ID, name="استان آزمون اول", level="province", parent_id=0),
                    Location(id=COUNTY_A_ID, name="شهرستان آزمون اول", level="county", parent_id=PROVINCE_A_ID),
                    Location(id=PROVINCE_B_ID, name="استان آزمون دوم", level="province", parent_id=0),
                    Location(id=COUNTY_B_ID, name="شهرستان آزمون دوم", level="county", parent_id=PROVINCE_B_ID),
                ]
            )
    submit_limiter.clear()
    login_limiter.clear()
    idempotency_store.clear()
    yield


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client


@pytest.fixture
async def admin_headers(client):
    response = await client.post("/api/v1/admin/login", data=ADMIN_LOGIN_BODY)
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def submit_form(
    client,
    payload: dict | None = None,
    files: dict | None = None,
    headers: dict | None = None,
):
    """POST /api/v1/submissions with multipart payload + files."""
    body = {"payload": json.dumps(payload if payload is not None else valid_payload(), ensure_ascii=False)}
    file_parts = files if files is not None else {
        "national_id_card": ("card.pdf", MINIMAL_PDF, "application/pdf"),
    }
    return await client.post("/api/v1/submissions", data=body, files=file_parts, headers=headers or {})
