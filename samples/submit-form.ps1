# نمونه ثبت فرم با PowerShell (بدون نیاز به چیزی جز curl.exe که در ویندوز هست)

# آدرس سرور را تغییر دهید
$baseUrl = "http://localhost:8000"

# ---------- ساخت payload ----------
$payload = [ordered]@{
    first_name             = "Ali"
    last_name              = "Rezaei"
    national_code          = "1234567891"          # نمونه معتبر؛ کد واقعی را بگذارید
    gender                 = "male"                # male | female
    birth_date             = "1370/05/10"          # شمسی YYYY/MM/DD
    military_status        = "served"              # برای مرد الزامی است
    education_degree       = "bachelor"
    education_field        = "Ravanshenasi"
    license_status         = "valid"               # valid | in_progress | none
    license_description    = "Parvaneh System Mosavvere"
    center_ownership       = "rented"              # owned | rented | other
    province_id            = 0                     # شناسه استان از GET /api/v1/locations/provinces
    county_id              = 0                     # شناسه شهرستان از GET /api/v1/locations/provinces/{id}/counties
    phone                  = "02112345678"
    postal_code            = "1234567890"
    address                = "Tehran, Azmoon St, No 1"
    mobile_number          = "09121234567"
    individual_rooms       = 2
    group_rooms            = 1
    child_rooms            = 0
    counselors_count       = 3
    has_waiting_space      = $true
    accepts_company_pattern = $true
    has_accessibility      = $false
    terms_accepted         = $true
}

# توجه: مقادیر province_id و county_id را از API موقعیت‌ها بگیرید:
# curl.exe -s "$baseUrl/api/v1/locations/provinces"

$json = $payload | ConvertTo-Json

# ---------- ارسال multipart ----------
# مسیر فایل‌ها را با فایل واقعی جایگزین کنید (PDF/JPG/PNG حداکثر ۵ مگابایت)
curl.exe -s -X POST "$baseUrl/api/v1/submissions" `
  -F "payload=$json" `
  -F "national_id_card=@C:\path\to\card.pdf;type=application/pdf" `
  -F "degree_document=@C:\path\to\degree.pdf;type=application/pdf"

# پاسخ موفق:
# {"success": true, "tracking_code": "FRK-XXXX", "message": "اطلاعات با موفقیت ثبت شد."}

# ---------- ورود مدیر و دریافت توکن ----------
curl.exe -s -X POST "$baseUrl/api/v1/admin/login" `
  -d "username=admin" `
  -d "password=ChangeMe@12345"

# ---------- فهرست فرم‌ها با توکن ----------
$token = "ACCESS_TOKEN_FROM_LOGIN"
curl.exe -s "$baseUrl/api/v1/admin/submissions?page=1&page_size=20" -H "Authorization: Bearer $token"

# ---------- دانلود خروجی اکسل ----------
curl.exe -s -o "export.xlsx" "$baseUrl/api/v1/admin/submissions/export.xlsx" -H "Authorization: Bearer $token"

# ---------- دانلود یک فایل پیوست ----------
curl.exe -s -o "file.pdf" "$baseUrl/api/v1/admin/submissions/1/files/1" -H "Authorization: Bearer $token"
