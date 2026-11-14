"""End-to-end API tests: submission flow, admin access, reports, security headers."""
import io
import json
import re

import openpyxl
import pytest

from app.core.config import get_settings
from app.core.idempotency import idempotency_store
from tests.conftest import (
    ADMIN_LOGIN_BODY,
    COUNTY_B_ID,
    MINIMAL_PDF,
    PROVINCE_A_ID,
    PROVINCE_B_ID,
    submit_form,
    valid_national_code,
    valid_payload,
    all_required_files,
)


async def get_admin_json(client, admin_headers, path):
    response = await client.get(path, headers=admin_headers)
    assert response.status_code == 200, response.text
    return response.json()["data"]


class TestPublicSubmission:
    async def test_successful_submission(self, client):
        response = await submit_form(client)
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["success"] is True
        assert re.fullmatch(r"FRK-[0-9A-F]{12}", body["tracking_code"])
        assert "با موفقیت" in body["message"]

    async def test_missing_required_field(self, client):
        payload = valid_payload()
        del payload["first_name"]
        response = await submit_form(client, payload=payload, files={})
        assert response.status_code == 422
        errors = response.json()["errors"]
        assert errors["first_name"] == "این فیلد الزامی است."

    async def test_invalid_national_code(self, client):
        response = await submit_form(client, payload=valid_payload(national_code="1234567890"))
        assert response.status_code == 422
        assert response.json()["errors"]["national_code"] == "کد ملی واردشده معتبر نیست."

    async def test_invalid_json_payload(self, client):
        response = await client.post(
            "/api/v1/submissions",
            data={"payload": "{not json"},
            files={"national_id_card": ("a.pdf", MINIMAL_PDF, "application/pdf")},
        )
        assert response.status_code == 422
        assert "payload" in response.json()["errors"]

    async def test_missing_payload_part(self, client):
        response = await client.post(
            "/api/v1/submissions",
            data={"something": "else"},
            files={"national_id_card": ("a.pdf", MINIMAL_PDF, "application/pdf")},
        )
        assert response.status_code == 422
        assert response.json()["errors"]["payload"] == "بخش payload الزامی است."

    async def test_terms_not_accepted(self, client):
        response = await submit_form(client, payload=valid_payload(terms_accepted=False))
        assert response.status_code == 422
        assert "قوانین" in response.json()["errors"]["terms_accepted"]

    async def test_county_province_mismatch(self, client):
        response = await submit_form(
            client, payload=valid_payload(province_id=PROVINCE_A_ID, county_id=COUNTY_B_ID)
        )
        assert response.status_code == 422
        assert "همخوانی" in response.json()["errors"]["county_id"]

    async def test_unknown_province(self, client):
        response = await submit_form(client, payload=valid_payload(province_id=777777, county_id=COUNTY_B_ID))
        assert response.status_code == 422
        assert "استان" in response.json()["errors"]["province_id"]

    async def test_negative_counter(self, client):
        response = await submit_form(client, payload=valid_payload(individual_rooms=-1))
        assert response.status_code == 422
        assert "منفی" in response.json()["errors"]["individual_rooms"]

    async def test_future_birth_date(self, client):
        response = await submit_form(client, payload=valid_payload(birth_date="1500/01/01"))
        assert response.status_code == 422
        assert "آینده" in response.json()["errors"]["birth_date"]

    async def test_invalid_mobile(self, client):
        response = await submit_form(client, payload=valid_payload(mobile_number="12345"))
        assert response.status_code == 422
        assert "همراه" in response.json()["errors"]["mobile_number"]

    async def test_tracking_codes_unique(self, client):
        first = (await submit_form(client)).json()["tracking_code"]
        second = (await submit_form(client)).json()["tracking_code"]
        assert first != second

    async def test_idempotency_key_replays_same_response(self, client):
        headers = {"Idempotency-Key": "abc-123"}
        first = await submit_form(client, headers=headers)
        second = await submit_form(client, headers=headers)
        assert first.status_code == 201 and second.status_code == 201
        assert first.json()["tracking_code"] == second.json()["tracking_code"]
        assert not idempotency_store.get("other-key")


class TestV10Rules:
    """قوانین نسخهٔ ۱۰: شماره پروانه، تلفن ثابت اجباری، همراه اختیاری، پروانه مرکز."""

    async def test_valid_license_requires_number(self, client):
        response = await submit_form(client, payload=valid_payload(license_number=None))
        assert response.status_code == 422, response.text
        errors = response.json()["errors"]
        assert "شماره پروانه" in errors.get("license_number", "")

    async def test_in_progress_license_without_number_ok(self, client):
        response = await submit_form(client, payload=valid_payload(
            license_status="in_progress", license_number=None))
        assert response.status_code == 201, response.text

    async def test_landline_required(self, client):
        response = await submit_form(client, payload=valid_payload(phone=None))
        assert response.status_code == 422, response.text
        errors = response.json()["errors"]
        assert "ثابت" in errors.get("phone", "")

    async def test_mobile_optional(self, client):
        response = await submit_form(client, payload=valid_payload(mobile_number=None))
        assert response.status_code == 201, response.text

    async def test_center_license_file_required(self, client):
        response = await submit_form(client, files={
            "national_id_card": ("card.pdf", MINIMAL_PDF, "application/pdf"),
            "degree_document": ("degree.pdf", MINIMAL_PDF, "application/pdf"),
        })
        assert response.status_code == 422, response.text
        errors = response.json()["errors"]
        assert "پروانه مرکز فعالیت" in errors.get("files.center_activity_license", "")


class TestCounterLimit:
    async def test_upper_limit_enforced_when_configured(self, client, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "MAX_COUNTER_VALUE", 5)
        response = await submit_form(client, payload=valid_payload(counselors_count=6))
        assert response.status_code == 422
        assert "بیش از 5" in response.json()["errors"]["counselors_count"]

    async def test_min_age_enforced_when_configured(self, client, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "MIN_AGE_YEARS", 30)
        response = await submit_form(client, payload=valid_payload(birth_date="1380/01/01"))
        assert response.status_code == 422
        assert "سن" in response.json()["errors"]["birth_date"]


class TestAdminAccess:
    async def test_login_success(self, client):
        response = await client.post("/api/v1/admin/login", data=ADMIN_LOGIN_BODY)
        assert response.status_code == 200
        assert response.json()["token_type"] == "bearer"

    async def test_login_wrong_password(self, client):
        response = await client.post(
            "/api/v1/admin/login", data={"username": "admin", "password": "wrong"}
        )
        assert response.status_code == 401

    async def test_admin_routes_require_token(self, client):
        for path in [
            "/api/v1/admin/submissions",
            "/api/v1/admin/submissions/1",
            "/api/v1/admin/submissions/1/files/1",
            "/api/v1/admin/submissions/export.xlsx",
        ]:
            response = await client.get(path)
            assert response.status_code == 401, path

    async def test_invalid_token_rejected(self, client):
        response = await client.get(
            "/api/v1/admin/submissions", headers={"Authorization": "Bearer not-a-jwt"}
        )
        assert response.status_code == 401


class TestAdminReports:
    async def test_list_pagination_and_filters(self, client, admin_headers):
        for _ in range(3):
            await submit_form(client)
        data = await get_admin_json(client, admin_headers, "/api/v1/admin/submissions?page=1&page_size=2")
        assert data["total"] == 3
        assert len(data["items"]) == 2

        data = await get_admin_json(
            client, admin_headers, f"/api/v1/admin/submissions?tracking_code={data['items'][0]['tracking_code']}"
        )
        assert data["total"] == 1

    async def test_date_filter(self, client, admin_headers):
        await submit_form(client)
        data = await get_admin_json(
            client, admin_headers, "/api/v1/admin/submissions?date_from=1400/01/01&date_to=1500/01/01"
        )
        assert data["total"] == 1
        response = await client.get(
            "/api/v1/admin/submissions?date_from=1370/01/01&date_to=1371/01/01", headers=admin_headers
        )
        assert response.json()["data"]["total"] == 0

    async def test_national_code_filter(self, client, admin_headers):
        await submit_form(client)
        code = valid_payload()["national_code"]
        data = await get_admin_json(
            client, admin_headers, f"/api/v1/admin/submissions?national_code={code}"
        )
        assert data["total"] == 1

    async def test_detail_contains_jalali_birth_date(self, client, admin_headers):
        await submit_form(client)
        data = await get_admin_json(client, admin_headers, "/api/v1/admin/submissions/1")
        assert data["birth_date_jalali"] == "1370/05/10"
        assert data["province_name"] == "استان آزمون اول"
        assert data["terms_accepted_at"] is not None

    async def test_detail_404(self, client, admin_headers):
        response = await client.get("/api/v1/admin/submissions/999", headers=admin_headers)
        assert response.status_code == 404

    async def test_print_data(self, client, admin_headers):
        await submit_form(client)
        data = await get_admin_json(client, admin_headers, "/api/v1/admin/submissions/1/print")
        labels = [field["label"] for field in data["fields"]]
        assert "کد پیگیری" in labels
        assert "جنسیت" in labels

    async def test_excel_export(self, client, admin_headers):
        await submit_form(client, payload=valid_payload(last_name="=HYPERLINK(\"http://evil\")"))
        response = await client.get("/api/v1/admin/submissions/export.xlsx", headers=admin_headers)
        assert response.status_code == 200
        assert "spreadsheetml" in response.headers["content-type"]

        workbook = openpyxl.load_workbook(io.BytesIO(response.content))
        sheet = workbook.active
        assert sheet.cell(row=1, column=1).value == "شناسه"
        assert sheet.cell(row=1, column=2).value == "کد پیگیری"
        last_name_cell = sheet.cell(row=2, column=4).value
        assert last_name_cell.startswith("'")  # formula injection neutralized

    async def test_file_download(self, client, admin_headers):
        content = b"%PDF-1.4 test-bytes"
        await submit_form(client, files=all_required_files(national_id_card=("doc.pdf", content, "application/pdf")))
        response = await client.get(
            "/api/v1/admin/submissions/1/files/1", headers=admin_headers
        )
        assert response.status_code == 200
        assert response.content == content
        assert "attachment" in response.headers["content-disposition"]

    async def test_file_download_cross_submission_denied(self, client, admin_headers):
        await submit_form(client)
        await submit_form(client)
        # File 1 belongs to submission 1, not submission 2
        response = await client.get(
            "/api/v1/admin/submissions/2/files/1", headers=admin_headers
        )
        assert response.status_code == 404


class TestLocationsAndOptions:
    async def test_provinces_and_counties(self, client):
        response = await client.get("/api/v1/locations/provinces")
        assert response.status_code == 200
        provinces = response.json()["data"]
        assert {"id": PROVINCE_A_ID, "name": "استان آزمون اول"} in provinces

        response = await client.get(f"/api/v1/locations/provinces/{PROVINCE_A_ID}/counties")
        counties = response.json()["data"]
        assert {"id": COUNTY_B_ID, "name": "شهرستان آزمون دوم"} not in counties

        response = await client.get("/api/v1/locations/provinces/999999/counties")
        assert response.status_code == 404

    async def test_form_options(self, client):
        response = await client.get("/api/v1/form/options")
        data = response.json()["data"]
        assert {"value": "male", "label": "مرد"} in data["genders"]
        assert "pdf" in data["allowed_extensions"]
        assert data["max_file_size_bytes"] == 5 * 1024 * 1024


class TestSecurityAndInfrastructure:
    async def test_health(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["database"] == "ok"

    async def test_correlation_id_header(self, client):
        response = await client.get("/health")
        assert response.headers["x-request-id"]

    async def test_security_headers(self, client):
        response = await client.get("/health")
        assert response.headers["x-content-type-options"] == "nosniff"
        assert "frame-ancestors 'self'" in response.headers["content-security-policy"]

    async def test_rate_limit_429(self, client, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "RATE_LIMIT_SUBMIT_PER_MINUTE", 2)
        for _ in range(2):
            response = await submit_form(client)
            assert response.status_code == 201
        response = await submit_form(client)
        assert response.status_code == 429

    async def test_request_size_limit_413(self, client, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "MAX_REQUEST_SIZE_BYTES", 1000)
        response = await submit_form(client)
        assert response.status_code == 413
