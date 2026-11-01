# راهنمای قرار دادن پروژه در گیت‌هاب و استقرار روی سرور

مسیر پروژه روی سیستم شما: `D:\projects\farakhan`

---

## بخش اول: قرار دادن پروژه در گیت‌هاب

### گام ۱ — بررسی گیت

```powershell
git --version
```

اگر نصب نیست، از [git-scm.com](https://git-scm.com/download/win) نصب کنید (در همان مسیر پیش‌فرض Next بزنید).

### گام ۲ — پیکربندی اولیه (فقط بار اول)

```powershell
git config --global user.name "نام شما"
git config --global user.email "ایمیل شما@example.com"
```

### گام ۳ — ساخت مخزن در گیت‌هاب

1. وارد [github.com](https://github.com) شوید.
2. دکمه **New repository** را بزنید.
3. نام مخزن: `farakhan`
4. **خطر مهم:** چون این برنامه اطلاعات شخصی (کد ملی، مدارک) را مدیریت می‌کند، مخزن را حتماً **Private** انتخاب کنید.
5. گزینه‌های «Add a README» و «.gitignore» و «license» را **خالی بگذارید** (ما خودمان داریم).
6. **Create repository** را بزنید و آدرس مخزن را کپی کنید، مثل:
   `https://github.com/USERNAME/farakhan.git`

### گام ۴ — راه‌اندازی گیت در پروژه و اولین push

```powershell
cd D:\projects\farakhan
git init
git add .
git commit -m "Initial commit: Farakhan cooperation form backend"
git branch -M main
git remote add origin https://github.com/USERNAME/farakhan.git
git push -u origin main
```

نکته‌ها:

- فایل `.gitignore` از قبل در پروژه هست و `.env`، `__pycache__`، `*.db` و محیط‌های مجازی را از مخزن **حذف** می‌کند. هرگز فایل `.env` واقعی را commit نکنید؛ فقط `.env.example` در مخزن است.
- موقع push از شما نام کاربری و رمز می‌خواهد؛ رمز گیت‌هاب معمولی قبول نیست و باید از **Personal Access Token** استفاده کنید:
  - GitHub → Settings → Developer settings → Personal access tokens → **Tokens (classic)** → Generate new token → تیک `repo` → تولید و کپی.
  - در قسمت Password همان توکن را بچسبانید.
- روش جایگزین ساده‌تر: نصب **GitHub Desktop** یا افزونه GitHub در **VS Code** و زدن دکمه‌های Publish/Push.

### گام ۵ — به‌روزرسانی‌های بعدی

```powershell
cd D:\projects\farakhan
git add .
git commit -m "توضیح تغییرات"
git push
```

### گام ۶ — کپی شدن پروژه روی هر سیستم دیگر

```powershell
git clone https://github.com/USERNAME/farakhan.git D:\projects\farakhan
```

---

## بخش دوم: استقرار روی سرور

### معماری استقرار

```
اینترنت → Nginx (HTTPS/443) → Docker: api (FastAPI:8000) → Docker: postgres (5432 داخلی)
```

- دیتابیس فقط داخل شبکه Docker قابل دسترسی است.
- فایل‌های کاربران در volume دیتابیس نگهداری می‌شوند.

### پیش‌نیاز سرور

یک سرور (VPS) با سیستم‌عامل **Ubuntu 22.04 یا جدیدتر**، حداقل ۲ گیگ رم، و دامنه‌ای که رکورد A آن به IP سرور اشاره کند.

### گام ۱ — ورود و به‌روزرسانی

```bash
ssh root@SERVER_IP
apt update && apt upgrade -y
```

### گام ۲ — نصب Docker و Docker Compose

```bash
curl -fsSL https://get.docker.com | sh
docker --version
docker compose version
```

### گام ۳ — فایروال

```bash
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

### گام ۴ — دریافت پروژه از گیت‌هاب

```bash
mkdir -p /opt/farakhan
cd /opt/farakhan
# روش private repo: یک توکن با دسترسی read بسازید و در آدرس بگذارید
git clone https://USERNAME:YOUR_TOKEN@github.com/USERNAME/farakhan.git app
cd app/backend
```

> اگر سرور اجازه اجرای git ندارد، می‌توانید zip پروژه را با `scp` هم منتقل کنید:
> `scp farakhan-backend.zip root@SERVER_IP:/opt/farakhan/` و بعد از حالت فشرده خارج کنید.

### گام ۵ — ساخت فایل محیطی تولید

```bash
cp .env.example .env
nano .env
```

این مقادیر را حتماً تغییر دهید:

| متغیر | مقدار تولید |
|---|---|
| `APP_ENV` | `production` |
| `SECRET_KEY` | خروجی دستور زیر |
| `ADMIN_PASSWORD` | یک رمز قوی و طولانی |
| `POSTGRES_PASSWORD` | رمز قوی جدید (و همان در `DATABASE_URL`) |
| `CORS_ORIGINS` | `https://form.your-domain.ir` |
| `ALLOWED_FRAME_ANCESTORS` | اگر فرم در دامنه دیگری iframe می‌شود، همان دامنه؛ وگرنه خالی |
| `TRUST_X_FORWARDED_FOR` | `true` (چون پشت Nginx هستید) |

تولید کلید امن:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### گام ۶ — اجرا و migration

```bash
docker compose up -d --build
docker compose exec api alembic upgrade head
docker compose exec api python -m app.db.seed_locations
curl http://127.0.0.1:8000/health
```

خروجی مورد انتظار: `{"status":"ok","database":"ok","app_env":"production"}`

### گام ۷ — Nginx به‌عنوان reverse proxy + HTTPS

```bash
apt install -y nginx certbot python3-certbot-nginx
nano /etc/nginx/sites-available/farakhan
```

محتوای فایل:

```nginx
server {
    listen 80;
    server_name form.your-domain.ir;

    client_max_body_size 30m;   # هماهنگ با MAX_REQUEST_SIZE_BYTES

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

فعال‌سازی و صدور گواهی رایگان HTTPS:

```bash
ln -s /etc/nginx/sites-available/farakhan /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
certbot --nginx -d form.your-domain.ir
```

Certbot تمدید خودکار را هم نصب می‌کند. از این لحظه سرویس روی
`https://form.your-domain.ir/docs` در دسترس است.

> نکته: تا وقتی `CORS_ORIGINS` دامنه فرانت‌اند را نداشته باشد، مرورگر فرانت‌اند خارجی را بلاک می‌کند؛ این رفتار صحیح است.

### گام ۸ — به‌روزرسانی نسخه جدید در آینده

```bash
cd /opt/farakhan/app
git pull
cd backend
docker compose up -d --build
docker compose exec api alembic upgrade head
```

### گام ۹ — پشتیبان‌گیری منظم (خیلی مهم)

داده‌ها (شامل فایل‌های اسکن‌شده) داخل PostgreSQL هستند:

```bash
# تهیه پشتیبان دستی
docker compose exec postgres pg_dump -U farakhan farakhan > backup_$(date +%F).sql

# بازگردانی
cat backup_2026-01-01.sql | docker compose exec -T postgres psql -U farakhan farakhan
```

یک cron روزانه هم اضافه کنید:

```bash
crontab -e
# اضافه کنید:
0 3 * * * cd /opt/farakhan/app/backend && docker compose exec postgres pg_dump -U farakhan farakhan > /opt/backups/farakhan_$(date +\%F).sql
```

### گام ۱۰ — مانیتورینگ و لاگ

```bash
docker compose ps                 # وضعیت سرویس‌ها و healthcheck
docker compose logs -f api        # لاگ زنده API
docker compose logs --since 1h api
```

### چک‌لیست نهایی استقرار

- [ ] `APP_ENV=production` در `.env`
- [ ] `SECRET_KEY` تصادفی و جدید
- [ ] `ADMIN_PASSWORD` قوی (و `ADMIN_USERNAME` پیش‌فرض نماند)
- [ ] `POSTGRES_PASSWORD` قوی و هماهنگ با `DATABASE_URL`
- [ ] `TRUST_X_FORWARDED_FOR=true` پشت Nginx
- [ ] HTTPS فعال با certbot
- [ ] `curl /health` پاسخ ok می‌دهد
- [ ] ورود مدیر و دانلود یک فایل تستی انجام شد
- [ ] cron پشتیبان‌گیری تنظیم شد
- [ ] مخزن گیت‌هاب Private است و `.env` در آن نیست (`git ls-files | grep .env$` خالی باشد)

### سناریوی ویندوز سرور (جایگزین)

اگر سرور ویندوزی است: Docker Desktop for Windows را نصب کنید، همین دستورهای
`docker compose ...` را در PowerShell اجرا کنید و به‌جای Nginx از IIS + ARR
یا مستقیماً گواهی و پورت مپینگ استفاده کنید. توصیه ما سرور لینوکسی است چون
دستورها و اسکریپت‌های بالا عیناً همان است.
