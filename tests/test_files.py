"""File upload handling: allowed types, size limits, magic bytes, duplicates, transactionality."""
import pytest

from tests.conftest import MINIMAL_JPEG, MINIMAL_PDF, MINIMAL_PNG, all_required_files, submit_form, valid_payload
from tests.test_api import get_admin_json


class TestAcceptedFiles:
    @pytest.mark.parametrize(
        "part", [
            ("national_id_card", ("card.pdf", MINIMAL_PDF, "application/pdf")),
            ("degree_document", ("scan.jpg", MINIMAL_JPEG, "image/jpeg")),
            ("center_permit", ("photo.png", MINIMAL_PNG, "image/png")),
        ]
    )
    async def test_valid_files_accepted(self, client, part):
        response = await submit_form(client, files=all_required_files(**{part[0]: part[1]}))
        assert response.status_code == 201, response.text

    async def test_metadata_stored(self, client, admin_headers):
        response = await submit_form(client, files=all_required_files(
            national_id_card=("کارت ملی.pdf", MINIMAL_PDF, "application/pdf")))
        assert response.status_code == 201
        data = await get_admin_json(client, admin_headers, "/api/v1/admin/submissions/1")
        files = data["files"]
        assert len(files) == 3  # v10: all three required files present
        assert files[0]["original_name"] == "کارت ملی.pdf"
        assert files[0]["mime_type"] == "application/pdf"
        assert files[0]["size_bytes"] == len(MINIMAL_PDF)
        assert files[0]["field_key"] == "national_id_card"


class TestRejectedFiles:
    async def test_disallowed_extension(self, client):
        response = await submit_form(client, files={
            "national_id_card": ("notes.txt", b"hello world text", "text/plain"),
        })
        assert response.status_code == 422
        assert "files.national_id_card" in response.json()["errors"]

    async def test_empty_file(self, client):
        response = await submit_form(client, files={
            "national_id_card": ("empty.pdf", b"", "application/pdf"),
        })
        assert response.status_code == 422
        assert "خالی" in response.json()["errors"]["files.national_id_card"]

    async def test_oversize_file(self, client):
        big_png = MINIMAL_PNG + b"\x00" * (5 * 1024 * 1024)
        response = await submit_form(client, files={
            "national_id_card": ("big.png", big_png, "image/png"),
        })
        assert response.status_code == 422
        assert "مگابایت" in response.json()["errors"]["files.national_id_card"]

    async def test_extension_content_mismatch(self, client):
        # .png extension but real PDF content
        response = await submit_form(client, files={
            "national_id_card": ("fake.png", MINIMAL_PDF, "image/png"),
        })
        assert response.status_code == 422
        assert "همخوانی" in response.json()["errors"]["files.national_id_card"]

    async def test_unknown_file_field(self, client):
        response = await submit_form(client, files={
            "hacked_field": ("x.pdf", MINIMAL_PDF, "application/pdf"),
        })
        assert response.status_code == 422
        assert "files.hacked_field" in response.json()["errors"]

    async def test_duplicate_field_rejected(self, client):
        response = await submit_form(client, files=[
            ("national_id_card", ("a.pdf", MINIMAL_PDF, "application/pdf")),
            ("national_id_card", ("b.pdf", MINIMAL_PDF, "application/pdf")),
        ])
        assert response.status_code == 422
        assert "فقط" in response.json()["errors"]["files.national_id_card"]


class TestTransactionality:
    async def test_invalid_file_rolls_back_everything(self, client, admin_headers):
        response = await submit_form(client, files={
            "national_id_card": ("ok.pdf", MINIMAL_PDF, "application/pdf"),
            "degree_document": ("bad.txt", b"not an image", "text/plain"),
        })
        assert response.status_code == 422

        listing = await get_admin_json(client, admin_headers, "/api/v1/admin/submissions")
        assert listing["total"] == 0  # nothing was persisted
