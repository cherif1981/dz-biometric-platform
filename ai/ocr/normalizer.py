"""تطبيع النصوص والتواريخ"""
import re


def normalize_arabic(text):
    """تطبيع النص العربي"""
    if not text:
        return text
    text = re.sub(r'[إأآا]', 'ا', text)
    text = re.sub(r'[ىي]', 'ي', text)
    text = re.sub(r'[ةه]', 'ة', text)
    return text.strip()


def normalize_date(date_str):
    """تطبيع التاريخ إلى صيغة YYYY-MM-DD"""
    if not date_str:
        return None
    date_str = date_str.replace('.', '/').replace('-', '/')
    parts = date_str.split('/')
    if len(parts) != 3:
        return None
    try:
        if len(parts[0]) == 4:
            return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
        else:
            return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
    except Exception:
        return None