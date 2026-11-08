"""Server-side printable PDF (A4) for a single submission.

Full Persian RTL support: text is shaped with arabic_reshaper and
bidi-reordered with python-bidi, rendered with the bundled Vazirmatn
font. The field content comes from print_service.build_print_data so
the PDF always matches the JSON print payload.

Layout (v4): colored header band + info strip (tracking code / registry ID /
date), numbered sections, compact two-pairs-per-row field grid with a
full-width row for long texts, zebra rows and a page footer.
"""
import io
import re
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.errors import AppError
from app.services.print_service import build_print_data

_FONT_DIR = Path(__file__).resolve().parent.parent / "static" / "fonts"
_FONT_REG = _FONT_DIR / "Vazirmatn-Regular.ttf"
_FONT_BOLD = _FONT_DIR / "Vazirmatn-Bold.ttf"

_reshaper = arabic_reshaper.ArabicReshaper(
    configuration={"delete_harakat": False, "support_ligatures": True}
)

# پالت چاپ (هم‌خوان با رنگ فرم، ملایم برای پرینتر)
_INK = colors.HexColor("#1c2b20")
_MUTED = colors.HexColor("#5c6f60")
_ACCENT = colors.HexColor("#1b7d68")
_ACCENT_DARK = colors.HexColor("#12564a")
_ACCENT_SOFT = colors.HexColor("#e6f2ee")
_LINE = colors.HexColor("#c9d7cc")
_ROW_ALT = colors.HexColor("#f6faf8")

_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

_PAGE_W = A4[0]
_MARGIN = 14 * mm
_CONTENT_W = _PAGE_W - 2 * _MARGIN  # ≈ 182mm


def _ensure_fonts() -> None:
    if not _FONT_REG.exists() or not _FONT_BOLD.exists():
        raise AppError(status_code=500, message="فونت فارسی برای ساخت پی‌دی‌اف روی سرور یافت نشد.")
    registered = pdfmetrics.getRegisteredFontNames()
    if "Vazirmatn" not in registered:
        pdfmetrics.registerFont(TTFont("Vazirmatn", str(_FONT_REG)))
    if "Vazirmatn-Bold" not in registered:
        pdfmetrics.registerFont(TTFont("Vazirmatn-Bold", str(_FONT_BOLD)))


def _fa_digits(s: str) -> str:
    """ارقام فارسی برای مقادیری که حروف لاتین ندارند (مثل کد ملی و تاریخ)."""
    if re.search(r"[A-Za-z]", s):
        return s
    return s.translate(_FA_DIGITS)


def fa(text, fa_digits: bool = False) -> str:
    """شکل‌دهی و چیدمان راست‌به‌چپ متن فارسی برای ReportLab."""
    if text is None:
        return ""
    s = str(text)
    if fa_digits:
        s = _fa_digits(s)
    return get_display(_reshaper.reshape(s), base_dir="R")


_ST_VALUE = ParagraphStyle(
    "value", fontName="Vazirmatn", fontSize=9.5, leading=14.5,
    alignment=TA_RIGHT, textColor=_INK,
)
_ST_VALUE_WIDE = ParagraphStyle(
    "value_wide", fontName="Vazirmatn", fontSize=9.5, leading=14.5,
    alignment=TA_RIGHT, textColor=_INK,
)
_ST_LABEL = ParagraphStyle(
    "label", fontName="Vazirmatn-Bold", fontSize=9.5, leading=14.5,
    alignment=TA_RIGHT, textColor=_ACCENT_DARK,
)
_ST_TITLE = ParagraphStyle(
    "title", fontName="Vazirmatn-Bold", fontSize=16.5, leading=23,
    alignment=TA_RIGHT, textColor=colors.white,
)
_ST_SUB = ParagraphStyle(
    "sub", fontName="Vazirmatn", fontSize=9.5, leading=14,
    alignment=TA_RIGHT, textColor=colors.HexColor("#dff0ea"),
)
_ST_SECTION = ParagraphStyle(
    "section", fontName="Vazirmatn-Bold", fontSize=11.5, leading=16,
    alignment=TA_RIGHT, textColor=_INK,
)
_ST_INFO_KEY = ParagraphStyle(
    "info_key", fontName="Vazirmatn-Bold", fontSize=8.5, leading=12,
    alignment=TA_CENTER, textColor=_MUTED,
)
_ST_INFO_VAL = ParagraphStyle(
    "info_val", fontName="Vazirmatn-Bold", fontSize=11, leading=16,
    alignment=TA_CENTER, textColor=_ACCENT_DARK,
)

_COL_W = [_CONTENT_W * 0.29, _CONTENT_W * 0.21, _CONTENT_W * 0.29, _CONTENT_W * 0.21]


def _kv_grid(rows: list[tuple[str, str, bool]]) -> Table:
    """شبکهٔ فیلدها: در هر سطر دو جفت (مقدار، برچسب)؛ فیلدهای بلند تمام‌عرض."""
    data = []
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.9, _LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, _LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        # پس‌زمینهٔ ستون‌های برچسب (ستون‌های ۱ و ۳)
        ("BACKGROUND", (1, 0), (1, -1), _ACCENT_SOFT),
        ("BACKGROUND", (3, 0), (3, -1), _ACCENT_SOFT),
    ]
    row_index = 0

    def _value_par(value: str, wide: bool = False):
        shaped = fa(value, fa_digits=not re.search(r"[A-Za-z]", str(value)))
        return Paragraph(shaped, _ST_VALUE_WIDE if wide else _ST_VALUE)

    def emit_pair_row(pair1, pair2=None) -> None:
        nonlocal row_index
        l1, v1 = pair1
        if pair2 is None:
            data.append([_value_par(v1), Paragraph(fa(l1), _ST_LABEL), "", ""])
        else:
            l2, v2 = pair2
            data.append([
                _value_par(v1), Paragraph(fa(l1), _ST_LABEL),
                _value_par(v2), Paragraph(fa(l2), _ST_LABEL),
            ])
            style.append(("BACKGROUND", (2, row_index), (2, row_index), _ROW_ALT))
        if row_index % 2 == 1:
            style.append(("BACKGROUND", (0, row_index), (0, row_index), _ROW_ALT))
        row_index += 1

    def emit_wide_row(label: str, value: str) -> None:
        nonlocal row_index
        data.append([_value_par(value, wide=True), "", "", Paragraph(fa(label), _ST_LABEL)])
        style.append(("SPAN", (0, row_index), (2, row_index)))
        row_index += 1

    pending: tuple[str, str] | None = None
    for label, value, wide in rows:
        value = value if value not in (None, "") else "—"
        if wide:
            if pending:
                emit_pair_row(pending)
                pending = None
            emit_wide_row(label, value)
        elif pending:
            emit_pair_row(pending, (label, value))
            pending = None
        else:
            pending = (label, value)
    if pending:
        emit_pair_row(pending)

    t = Table(data, colWidths=_COL_W, hAlign="RIGHT")
    t.setStyle(TableStyle(style))
    return t


def _section_title(num: str, text: str):
    return Paragraph(
        f'<font color="#1b7d68">{fa(num)}</font>&nbsp;&nbsp;{fa(text)}',
        _ST_SECTION,
    )


def build_submission_pdf(submission) -> bytes:
    """ساخت فایل PDF قابل چاپ برای یک فرم ثبت‌شده."""
    _ensure_fonts()
    data = build_print_data(submission)
    fields = {f["label"]: f["value"] for f in data["fields"]}

    def val(label: str) -> str:
        v = fields.get(label, "—")
        return "—" if v in (None, "") else str(v)

    edu_desc_label = "توضیحات مدرک (سایر)" if "توضیحات مدرک (سایر)" in fields else "رشته تحصیلی"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=_MARGIN, rightMargin=_MARGIN, topMargin=12 * mm, bottomMargin=18 * mm,
        title="فرم همکاری مرکز مشاوره — " + data["tracking_code"],
        author="Farakhan",
    )

    story = []

    # ---------- نوار سربرگ رنگی ----------
    band = Table(
        [[
            Paragraph(fa("سامانه فراخوان"), _ST_TITLE),
            Paragraph(fa("برگهٔ ثبت همکاری مرکز مشاوره"), _ST_SUB),
        ]],
        colWidths=[_CONTENT_W * 0.5, _CONTENT_W * 0.5], hAlign="RIGHT",
    )
    band.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _ACCENT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    story.append(band)
    story.append(Spacer(1, 4 * mm))

    # ---------- نوار مشخصات (کد پیگیری / شماره ثبت / تاریخ ثبت) ----------
    created_jalali = val("تاریخ ثبت فرم")
    info = Table(
        [[
            [Paragraph(fa("کد پیگیری"), _ST_INFO_KEY), Paragraph(fa(data["tracking_code"]), _ST_INFO_VAL)],
            [Paragraph(fa("شماره ثبت"), _ST_INFO_KEY), Paragraph(fa(_fa_digits(str(data["submission_id"]))), _ST_INFO_VAL)],
            [Paragraph(fa("تاریخ ثبت"), _ST_INFO_KEY), Paragraph(fa(created_jalali, fa_digits=True), _ST_INFO_VAL)],
        ]],
        colWidths=[_CONTENT_W / 3.0] * 3, hAlign="RIGHT",
    )
    info.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.9, _ACCENT),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, _LINE),
        ("BACKGROUND", (0, 0), (-1, -1), _ACCENT_SOFT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(info)
    story.append(Spacer(1, 6 * mm))

    # ---------- بخش‌ها ----------
    def section(num: str, title: str, rows: list[tuple[str, str, bool]]):
        story.append(KeepTogether([
            _section_title(num, title),
            Spacer(1, 1.5 * mm),
            _kv_grid(rows),
        ]))
        story.append(Spacer(1, 5 * mm))

    section("۱", "مشخصات متقاضی", [
        ("نام و نام خانوادگی", val("نام و نام خانوادگی"), False),
        ("کد ملی", val("کد ملی"), False),
        ("جنسیت", val("جنسیت"), False),
        ("تاریخ تولد", val("تاریخ تولد"), False),
        ("وضعیت سربازی", val("وضعیت سربازی"), False),
        ("شماره همراه", val("شماره همراه"), False),
        ("تلفن ثابت", val("تلفن ثابت"), False),
        ("کدپستی", val("کدپستی"), False),
        ("استان / شهرستان", val("استان") + " / " + val("شهرستان"), True),
        ("نشانی", val("نشانی"), True),
    ])

    section("۲", "تحصیلات و پروانه فعالیت", [
        ("مدرک تحصیلی", val("مدرک تحصیلی"), False),
        ("وضعیت پروانه", val("وضعیت پروانه"), False),
        (edu_desc_label, val(edu_desc_label), True),
        ("توضیحات پروانه", val("توضیحات پروانه"), True),
    ])

    section("۳", "مشخصات مرکز و ظرفیت‌ها", [
        ("مالکیت مرکز", val("مالکیت مرکز"), False),
        ("تعداد مشاوران", val("تعداد مشاوران"), False),
        ("اتاق‌های مشاوره فردی", val("اتاق‌های مشاوره فردی"), False),
        ("اتاق‌های مشاوره گروهی", val("اتاق‌های مشاوره گروهی"), False),
        ("اتاق‌های مشاوره کودک", val("اتاق‌های مشاوره کودک"), False),
        ("فضای انتظار", val("فضای انتظار"), False),
        ("پذیرش الگوی شرکت", val("پذیرش الگوی شرکت"), False),
        ("سهولت دسترسی", val("سهولت دسترسی"), False),
    ])

    # ---------- مدارک بارگذاری‌شده ----------
    file_rows = [
        (f["label"], f"{f['file_name']} ({round(f['size_bytes'] / 1024)} کیلوبایت)", True)
        for f in data["files"]
    ] or [("مدارک", "فایلی بارگذاری نشده است", True)]
    section("۴", "مدارک بارگذاری‌شده", file_rows)

    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Vazirmatn", 8)
        canvas.setFillColor(_MUTED)
        canvas.setStrokeColor(_LINE)
        canvas.setLineWidth(0.6)
        canvas.line(_MARGIN, 12 * mm, _PAGE_W - _MARGIN, 12 * mm)
        canvas.drawRightString(_PAGE_W - _MARGIN, 7 * mm, fa("سامانه فراخوان — برگهٔ ثبت همکاری مرکز مشاوره"))
        canvas.drawCentredString(_PAGE_W / 2, 7 * mm, "صفحهٔ " + fa(str(canvas.getPageNumber()), fa_digits=True))
        canvas.drawString(_MARGIN, 7 * mm, fa("تاریخ ثبت: ") + fa(created_jalali, fa_digits=True))
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
