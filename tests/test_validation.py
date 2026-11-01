"""Unit tests for validation utilities and business rules."""
import pytest

from app.utils.national_code import is_valid_national_code, mask_national_code
from app.utils.persian_digits import to_english_digits
from app.utils.phone import is_valid_mobile, is_valid_landline, normalize_phone
from app.utils.jalali_date import format_jalali, parse_jalali_date
from app.utils.tracking_code import generate_tracking_code, TRACKING_CODE_PREFIX
from app.schemas.submission import SubmissionCreate

from tests.conftest import valid_national_code, valid_payload


class TestNationalCode:
    def test_valid_codes(self):
        assert is_valid_national_code("1234567891") is True
        assert is_valid_national_code(valid_national_code("987654321")) is True

    def test_invalid_checksum(self):
        assert is_valid_national_code("1234567890") is False
        assert is_valid_national_code("1234567892") is False

    def test_wrong_length(self):
        assert is_valid_national_code("12345") is False
        assert is_valid_national_code("12345678901") is False

    def test_all_same_digits_invalid(self):
        assert is_valid_national_code("0000000000") is False
        assert is_valid_national_code("1111111111") is False

    def test_persian_digits_accepted(self):
        valid = valid_national_code("123456789")
        persian = valid.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
        assert is_valid_national_code(persian) is True

    def test_masking(self):
        masked = mask_national_code("1234567891")
        assert masked.startswith("1234")
        assert "*" in masked
        assert masked != "1234567891"


class TestPersianDigits:
    def test_translation(self):
        assert to_english_digits("۱۲۳۴") == "1234"
        assert to_english_digits("٠١٢") == "012"
        assert to_english_digits("abc123") == "abc123"


class TestPhone:
    def test_mobile_normal(self):
        assert is_valid_mobile("09123456789") is True

    def test_mobile_without_leading_zero(self):
        assert normalize_phone("9123456789") == "09123456789"

    def test_mobile_with_country_code(self):
        assert normalize_phone("+98 912 345 6789") == "09123456789"
        assert normalize_phone("00989123456789") == "09123456789"
        assert normalize_phone("989123456789") == "09123456789"

    def test_mobile_invalid(self):
        assert is_valid_mobile("12345") is False
        assert is_valid_mobile("08123456789") is False
        assert is_valid_mobile("0912345678") is False

    def test_landline(self):
        assert is_valid_landline("02112345678") is True
        assert is_valid_landline("021-12345678") is True
        assert is_valid_landline("09123456789") is False  # mobile is not a landline
        assert is_valid_landline("12345678") is False


class TestJalaliDate:
    def test_valid(self):
        parsed = parse_jalali_date("1370/05/10")
        assert parsed is not None
        assert parsed.year == 1370 and parsed.month == 5 and parsed.day == 10

    def test_dash_separator(self):
        assert parse_jalali_date("1370-05-10") is not None

    def test_invalid_month(self):
        assert parse_jalali_date("1370/13/01") is None

    def test_invalid_day(self):
        assert parse_jalali_date("1370/07/31") is None  # Mehr has 30 days

    def test_future_rejected_flag(self):
        from app.utils.jalali_date import is_future_jalali_date

        assert is_future_jalali_date(parse_jalali_date("1500/01/01")) is True
        assert is_future_jalali_date(parse_jalali_date("1370/05/10")) is False

    def test_format_roundtrip(self):
        from datetime import date

        gregorian = parse_jalali_date("1370/05/10").togregorian()
        assert format_jalali(gregorian) == "1370/05/10"


class TestTrackingCode:
    def test_format(self):
        code = generate_tracking_code()
        assert code.startswith(TRACKING_CODE_PREFIX + "-")
        hex_part = code.split("-")[1]
        assert len(hex_part) == 12
        int(hex_part, 16)  # must be valid hex

    def test_uniqueness(self):
        codes = {generate_tracking_code() for _ in range(500)}
        assert len(codes) == 500


class TestPayloadRules:
    def base(self, **overrides):
        data = valid_payload(**overrides)
        return data

    def test_valid_payload_ok(self):
        model = SubmissionCreate.model_validate(self.base())
        assert model.gender == "male"
        assert model.military_status == "served"

    def test_female_military_nulled(self):
        model = SubmissionCreate.model_validate(self.base(gender="female", military_status="served"))
        assert model.military_status is None

    def test_male_without_military_rejected(self):
        with pytest.raises(ValueError, match="سربازی"):
            SubmissionCreate.model_validate(self.base(military_status=None))

    def test_invalid_national_code_rejected(self):
        with pytest.raises(ValueError, match="کد ملی"):
            SubmissionCreate.model_validate(self.base(national_code="1234567890"))

    def test_postal_code_length(self):
        with pytest.raises(ValueError, match="کدپستی"):
            SubmissionCreate.model_validate(self.base(postal_code="12345"))

    def test_terms_must_be_true(self):
        with pytest.raises(ValueError, match="قوانین"):
            SubmissionCreate.model_validate(self.base(terms_accepted=False))

    def test_license_none_nulls_description(self):
        model = SubmissionCreate.model_validate(
            self.base(license_status="none", license_description="توضیح")
        )
        assert model.license_description is None
