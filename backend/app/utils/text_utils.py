import re


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()