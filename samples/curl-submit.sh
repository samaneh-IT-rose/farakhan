#!/usr/bin/env bash
# نمونه ثبت فرم با curl (لینوکس/مک)
BASE_URL="http://localhost:8000"

# شناسه استان و شهرستان:
curl -s "$BASE_URL/api/v1/locations/provinces"

cat > /tmp/payload.json <<'JSON'
{
  "first_name": "علی",
  "last_name": "رضایی",
  "national_code": "1234567891",
  "gender": "male",
  "birth_date": "1370/05/10",
  "military_status": "served",
  "education_degree": "bachelor",
  "education_field": "روانشناسی",
  "license_status": "valid",
  "license_description": "پروانه معتبر",
  "center_ownership": "rented",
  "province_id": 1,
  "county_id": 2,
  "phone": "02112345678",
  "postal_code": "1234567890",
  "address": "تهران، خیابان آزمون، پلاک ۱",
  "mobile_number": "09121234567",
  "individual_rooms": 2,
  "group_rooms": 1,
  "child_rooms": 0,
  "counselors_count": 3,
  "has_waiting_space": true,
  "accepts_company_pattern": true,
  "has_accessibility": false,
  "terms_accepted": true
}
JSON

curl -s -X POST "$BASE_URL/api/v1/submissions" \
  -F "payload=</tmp/payload.json" \
  -F "national_id_card=@./card.pdf;type=application/pdf" \
  -F "degree_document=@./degree.pdf;type=application/pdf"

# ورود مدیر
curl -s -X POST "$BASE_URL/api/v1/admin/login" -d "username=admin" -d "password=ChangeMe@12345"

# فهرست (توکن را جایگزین کنید)
curl -s "$BASE_URL/api/v1/admin/submissions" -H "Authorization: Bearer TOKEN"

# خروجی اکسل
curl -s -o export.xlsx "$BASE_URL/api/v1/admin/submissions/export.xlsx" -H "Authorization: Bearer TOKEN"
