# بک‌اند فرم فراخوان همکاری

بک‌اند امن، قابل‌آزمون و آماده استقرار برای «فرم فراخوان همکاری» بر پایه **FastAPI + PostgreSQL + SQLAlchemy 2 + Alembic + Docker**.

- ثبت فرم چندبخشی همراه با فایل‌ها در **یک تراکنش واحد**
- ذخیره فایل‌ها در PostgreSQL (نوع `BYTEA`) بدون دسترسی عمومی مستقیم
- اعتبارسنجی کامل سمت سرور (کد ملی، تاریخ شمسی، موبایل/ثابت، کدپستی، فیلدهای شرطی)
- پنل مدیریتی محافظت‌شده با JWT + فهرست، جزئیات، دانلود امن فایل، خروجی Excel و داده قابل چاپ
- مستندات تعاملی OpenAPI در مسیر `/docs`

---

## ۱. پیش‌نیازها

| روش | پیش‌نیاز |
|---|---|
| Docker (توصیه‌شده) | Docker Desktop روی ویندوز یا Docker Engine روی سرور |
| اجرای محلی | Python 3.12+ و PostgreSQL 14+ |

## ۲. راه‌اندازی سریع با Docker

```bash
cd backend

# ۱) ساخت فایل محیطی از نمونه
cp .env.example .env        # ویندوز PowerShell:  Copy-Item .env.example .env

# ۲) مقادیر SECRET_KEY و ADMIN_PASSWORD را حتماً تغییر دهید
#    تولید کلید قوی:  python -c "import secrets; print(secrets.token_hex(32))"

# ۳) بالا آوردن سرویس‌ها
docker compose up -d --build

# ۴) اجرای migration روی دیتابیس خالی
docker compose exec api alembic upgrade head

# ۵) درج استان‌ها و شهرستان‌های ایران (idempotent است)
docker compose exec api python -m app.db.seed_locations
```

سپس:

- مستندات تعاملی: `http://localhost:8000/docs`
- بررسی سلامت: `http://localhost:8000/health`
- ورود مدیر: `POST /api/v1/admin/login` با `ADMIN_USERNAME` / `ADMIN_PASSWORD`

## ۳. اجرای محلی بدون Docker

```bash
cd backend
python -m venv .venv
# ویندوز:  .venv\Scripts\activate      لینوکس:  source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

cp .env.example .env
# DATABASE_URL را به localhost تغییر دهید:
# DATABASE_URL=postgresql+asyncpg://farakhan:PASSWORD@localhost:5432/farakhan

alembic upgrade head
python -m app.db.seed_locations
uvicorn app.main:app --reload --port 8000
```

## ۴. اجرای آزمون‌ها

```bash
pip install -r requirements-dev.txt
pytest -v
```

آزمون‌ها روی SQLite درون‌حافظه اجرا می‌شوند و کاملاً ایزوله‌اند (بدون داده واقعی).
داخل Docker هم می‌توانید اجرا کنید:

```bash
docker compose --profile test run --rm test
```

## ۵. متغیرهای محیطی مهم

| متغیر | توضیح |
|---|---|
| `DATABASE_URL` | آدرس دیتابیس؛ داخل compose هاست `postgres` است |
| `SECRET_KEY` | کلید امضای JWT — در تولید حتماً تصادفی و طولانی |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | حساب مدیر (فقط از env، هرگز در کد) |
| `CORS_ORIGINS` | دامنه‌های مجاز فرانت‌اند، جدا شده با کاما |
| `ALLOWED_FRAME_ANCESTORS` | دامنه‌های مجاز برای iframe (CSP frame-ancestors) |
| `MAX_FILE_SIZE_BYTES` | حداکثر حجم هر فایل (پیش‌فرض ۵ مگابایت) |
| `MAX_REQUEST_SIZE_BYTES` | حداکثر حجم کل درخواست (پیش‌فرض ۳۰ مگابایت) |
| `RATE_LIMIT_SUBMIT_PER_MINUTE` | سقف ثبت فرم در دقیقه برای هر IP |
| `TRUST_X_FORWARDED_FOR` | فقط پشت reverse proxy معتبر `true` کنید |
| `REQUIRED_FILE_FIELDS` | فیلدهای فایل اجباری، مثل `national_id_card,degree_document` |
| `MIN_AGE_YEARS` / `MAX_COUNTER_VALUE` | سقف سن / شمارنده‌ها (۰ = غیرفعال، نیازمند تأیید مالک محصول) |

فهرست کامل تصمیم‌های باز و پیش‌فرض‌ها: [`docs/open-decisions.md`](docs/open-decisions.md)

## ۶. قرارداد API (نسخه `/api/v1`)

| متد و مسیر | دسترسی | کاربرد |
|---|---|---|
| `GET /form/options` | عمومی | گزینه‌های ثابت فرم (جنسیت، مقاطع، وضعیت‌ها، قواعد فایل) |
| `GET /locations/provinces` | عمومی | فهرست استان‌ها |
| `GET /locations/provinces/{province_id}/counties` | عمومی | شهرستان‌های استان |
| `POST /submissions` | عمومی + rate limit | ثبت فرم و فایل‌ها (multipart) |
| `POST /admin/login` | عمومی + rate limit | دریافت توکن JWT مدیر |
| `GET /admin/submissions` | مدیر | فهرست صفحه‌بندی‌شده (بدون محتوای باینری) |
| `GET /admin/submissions/{id}` | مدیر | جزئیات کامل یک فرم |
| `GET /admin/submissions/{id}/files/{file_id}` | مدیر | دانلود امن فایل |
| `GET /admin/submissions/export.xlsx` | مدیر | خروجی Excel (بدون محتوای باینری) |
| `GET /admin/submissions/{id}/print` | مدیر | داده ساختاریافته برای چاپ/PDF |
| `GET /health` | عمومی | بررسی سلامت سرویس و دیتابیس |

### ثبت فرم — `POST /api/v1/submissions`

درخواست از نوع `multipart/form-data` است:

- بخش `payload`: رشته JSON با ساختار `SubmissionCreate`
- فایل‌ها: هر فایل با نام فیلد خودش، مثل `national_id_card`، `degree_document`، ...

کلیدهای مجاز فایل:

```
military_card, national_id_card, degree_document, professional_license,
center_activity_license, center_permit, property_documents
```

پاسخ موفق (201):

```json
{
  "success": true,
  "tracking_code": "FRK-A1B2C3D4E5F6",
  "message": "اطلاعات با موفقیت ثبت شد."
}
```

پاسخ خطا (422):

```json
{
  "success": false,
  "message": "اطلاعات ارسالی معتبر نیست.",
  "errors": { "national_code": "کد ملی واردشده معتبر نیست." }
}
```

نمونه‌های آماده: [`samples/curl-submit.sh`](samples/curl-submit.sh) و [`samples/submit-form.ps1`](samples/submit-form.ps1)

### نکات قراردادی

- همه پاسخ‌ها `success` + `message` (فارسی) و در خطا `errors` به تفکیک فیلد دارند.
- خطاهای اعتبارسنجی با کد `422`، سقف نرخ با `429`، حجم بیش از حد با `413` برمی‌گردند.
- هر پاسخ دارای هدر `X-Request-ID` برای پیگیری است.
- هدر `Idempotency-Key` اختیاری است: ارسال مجدد با همان کلید، همان پاسخ را برمی‌گرداند و ثبت تکراری نمی‌سازد.
- `terms_accepted` باید `true` باشد؛ زمان پذیرش قوانین روی **سرور** ثبت می‌شود.
- تاریخ تولد ورودی شمسی (`YYYY/MM/DD`) است و خروجی هم شمسی + میلادی ذخیره می‌شود.
- کد ملی به صورت رشته ذخیره می‌شود (صفر ابتدایی حفظ می‌شود) و **یکتا نیست** (تصمیم #۱۴).
- در فهرست‌ها فقط metadata فایل‌ها می‌آید؛ محتوای باینری هرگز در JSON/Excel نمی‌آید.

## ۷. فرمت خطای یکپارچه و کدهای وضعیت

| کد | معنا |
|---|---|
| 200/201 | موفق |
| 400 | درخواست multipart نامعتبر |
| 401 | عدم احراز هویت مدیر |
| 404 | منبع یافت نشد |
| 409 | خطای یکپارچگی داده |
| 413 | حجم درخواست بیش از حد |
| 422 | اعتبارسنجی ناموفق (پیام‌های فارسی به تفکیک فیلد) |
| 429 | سقف نرخ درخواست |
| 500 | خطای داخلی (جزئیات فنی به کاربر نمایش داده نمی‌شود) |

## ۸. امنیت

- احراز هویت مدیر با JWT (`Authorization: Bearer`).
- دانلود فایل فقط برای مدیر و فقط اگر فایل متعلق به همان فرم باشد.
- نوع فایل با **امضای محتوایی (magic bytes)** بررسی می‌شود؛ پسوند و MIME اعلامی قابل اعتماد نیستند.
- نام فایل پاک‌سازی می‌شود؛ فایل روی دیسک نوشته نمی‌شود (ذخیره در BYTEA) پس path traversal موضوعیت ندارد.
- خروجی Excel در برابر formula injection ایمن‌سازی می‌شود.
- کد ملی، شماره تماس، محتوای فایل و رمزها در لاگ ثبت نمی‌شوند؛ لاگ فقط متد/مسیر/کد وضعیت است.
- CORS فقط برای originهای مشخص؛ `frame-ancestors` قابل تنظیم؛ هدرهای `nosniff` و `Referrer-Policy` فعال‌اند.
- اجرای کانتینر با کاربر غیر root؛ هیچ secret واقعی در مخزن نیست (`.env` در `.gitignore`).

## ۹. Migration ها

- ساختار دیتابیس **فقط** با Alembic مدیریت می‌شود؛ در startup هیچ جدولی خودکار ساخته نمی‌شود.
- `alembic upgrade head` روی دیتابیس خالی تست شده است.
- برای ساخت migration جدید: `alembic revision --autogenerate -m "..."` و سپس بازبینی دستی.
- rollback: `alembic downgrade -1`

## ۱۰. دستورهای پرکاربرد Docker

```bash
docker compose up -d --build          # ساخت و اجرا
docker compose logs -f api            # مشاهده لاگ
docker compose down                   # توقف
docker compose restart api            # ری‌استارت
docker compose exec api alembic upgrade head
docker compose exec api python -m app.db.seed_locations
docker compose --profile test run --rm test
```

## ۱۱. استقرار روی سرور و انتشار در گیت‌هاب

راهنمای گام‌به‌گام: [`docs/github-and-server-guide.fa.md`](docs/github-and-server-guide.fa.md)
