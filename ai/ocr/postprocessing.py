import re


def clean_text(text: str) -> str:
    """Normalize whitespace and remove artifacts."""
    text = re.sub(r"\s+", " ", text)
    text = text.replace("|", "I").replace("0", "O") if _is_alpha(text) else text
    return text.strip()


def _is_alpha(text: str) -> bool:
    return sum(c.isalpha() for c in text) > len(text) * 0.7