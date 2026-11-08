"""اعتبارسنجی کدپستی ۱۰ رقمی ایران.

ساختار رسمی کدپستی ایران (شرکت ملی پست): ۱۰ رقم؛ پنج رقم اول «کد بخش پستی»
(استان/شهرستان/محله) و پنج رقم دوم «کد نقطه تحویل». رقم اول «کد استان‌گروه»
است و در عمل کدپستی‌های ایران با بلوک‌های دوریقمی مشخصی شروع می‌شوند:

    ۱۱ تا ۱۹  →  تهران
    ۳۱ تا ۳۹  →  البرز، قزوین، قم، مرکزی، سمنان
    ۴۳ تا ۴۹  →  گیلان، مازندران، گلستان، زنجان
    ۵۱ تا ۵۹  →  آذربایجان شرقی، آذربایجان غربی، اردبیل
    ۶۳ تا ۶۹  →  خوزستان، ایلام، کرمانشاه، کردستان، همدان، لرستان
    ۷۱ تا ۷۹  →  فارس، بوشهر، هرمزگان، کرمان، کهگیلویه و بویراحمد
    ۸۱ تا ۸۹  →  اصفهان، یزد، چهارمحال و بختیاری
    ۹۱ تا ۹۹  →  خراسان رضوی، خراسان شمالی، خراسان جنوبی، سیستان و بلوچستان

بنابراین کدهایی که با ۰ یا ۲ شروع شوند یا بلوک دوریقمشان خارج از این
بازه‌ها باشد، هرگز معتبر نیستند. منبع نگاشت استان‌ها: parsipost.ir/blog/postal-code
"""
from app.utils.persian_digits import to_english_digits

POSTAL_CODE_MESSAGE = (
    "کدپستی باید ۱۰ رقم و مطابق الگوی کدپستی ایران باشد؛ رقم اول آن یکی از "
    "ارقام ۱، ۳ تا ۹ است (مانند ۱۹۶۸۸۴۵۵۳۲)."
)
POSTAL_PROVINCE_MESSAGE = "کدپستی واردشده با استان انتخاب‌شده همخوانی ندارد."

# بازه‌های مجاز بلوک دوریقم بر اساس رقم اول
POSTAL_GROUP_RANGES: dict[int, list[tuple[int, int]]] = {
    1: [(11, 19)],
    3: [(31, 39)],
    4: [(43, 49)],
    5: [(51, 59)],
    6: [(63, 69)],
    7: [(71, 79)],
    8: [(81, 89)],
    9: [(91, 99)],
}

# نگاشت نام استان (مطابق داده‌های seed) به گروه رقم اول
PROVINCE_POSTAL_GROUP: dict[str, int] = {
    "تهران": 1,
    "البرز": 3, "قزوین": 3, "قم": 3, "مرکزی": 3, "سمنان": 3,
    "گیلان": 4, "مازندران": 4, "گلستان": 4, "زنجان": 4,
    "آذربایجان شرقی": 5, "آذربایجان غربی": 5, "اردبیل": 5,
    "خوزستان": 6, "ایلام": 6, "کرمانشاه": 6, "کردستان": 6, "همدان": 6, "لرستان": 6,
    "فارس": 7, "بوشهر": 7, "هرمزگان": 7, "کرمان": 7, "کهگیلویه و بویراحمد": 7,
    "اصفهان": 8, "یزد": 8, "چهارمحال و بختیاری": 8,
    "خراسان رضوی": 9, "خراسان شمالی": 9, "خراسان جنوبی": 9, "سیستان و بلوچستان": 9,
}


def normalize_postal_code(value) -> str | None:
    """ارقام فارسی/عربی به انگلیسی و حذف فاصله و خط تیره."""
    if value is None:
        return None
    cleaned = to_english_digits(str(value)).strip().replace("-", "").replace(" ", "")
    return cleaned or None


def is_valid_postal_code_format(code: str | None) -> bool:
    """۱۰ رقم + بلوک دوریقم در بازه‌های رسمی."""
    code = normalize_postal_code(code)
    if not code or len(code) != 10 or not code.isdigit():
        return False
    first, block = int(code[0]), int(code[:2])
    ranges = POSTAL_GROUP_RANGES.get(first)
    if not ranges:
        return False
    return any(lo <= block <= hi for lo, hi in ranges)


def postal_code_matches_province(code: str | None, province_name: str | None) -> bool | None:
    """همخوانی کدپستی با استان.

    خروجی None یعنی استان ناشناخته است (بازرسی استان را نمی‌توان انجام داد)؛
    خروجی False یعنی قطعاً با استان همخوانی ندارد.
    """
    code = normalize_postal_code(code)
    if not code or not province_name:
        return None
    group = PROVINCE_POSTAL_GROUP.get(str(province_name).strip())
    if group is None:
        return None
    ranges = POSTAL_GROUP_RANGES.get(group, [])
    block = int(code[:2]) if code[:2].isdigit() else -1
    return any(lo <= block <= hi for lo, hi in ranges)
