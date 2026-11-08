"""مرتب‌سازی الفبایی فارسی.

مرتب‌سازی پیش‌فرض پایگاه‌داده (بر اساس کد یونیکد) ترتیب درست الفبای فارسی
نمی‌دهد؛ این ماژول یک کلید مرتب‌سازی استاندارد فارسی می‌سازد:

- هم‌ارزها نرمال می‌شوند (ي→ی، ك→ک، أ/إ→ا، ة→ه) و «آ» هم‌ارز «ا» در نظر
  گرفته می‌شود (مثل فرهنگ‌نویسی متعارف).
- فاصله و نیم‌فاصله پیش از حروف قرار می‌گیرند تا واژه‌های کوتاه‌تر اول بیایند.
- ترتیب حروف: ا ب پ ت ث ج چ ح خ د ذ ر ز ژ س ش ص ض ط ظ ع غ ف ق ک گ ل م ن و ه ی
"""


_ORDER = {}
for _i, _ch in enumerate("ابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی"):
    _ORDER[_ch] = _i

_NORMALIZE = {
    "ي": "ی",
    "ك": "ک",
    "أ": "ا",
    "إ": "ا",
    "آ": "ا",
    "ة": "ه",
    "ۀ": "ه",
    "ؤ": "و",
    "ئ": "ی",
    "\u200c": " ",  # نیم‌فاصله
    "\u200f": "",
    "\u200e": "",
}


def persian_alpha_key(text: str) -> tuple:
    """کلید مرتب‌سازی الفبایی فارسی برای استفاده در sorted()."""
    s = str(text or "")
    for src, dst in _NORMALIZE.items():
        s = s.replace(src, dst)
    key = []
    for ch in s:
        if ch == " ":
            key.append((0, -1, 0))
        elif ch in _ORDER:
            key.append((0, _ORDER[ch], 0))
        elif ch.isdigit():
            key.append((1, 0, int(ch)))
        else:
            key.append((2, 0, ord(ch)))
    return key


def sorted_persian(items, key=lambda item: item):
    """مرتب‌سازی یک فهرست بر اساس ترتیب الفبای فارسی."""
    return sorted(items, key=lambda item: persian_alpha_key(key(item)))
