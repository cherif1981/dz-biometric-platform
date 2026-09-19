from datetime import datetime


def validate_date(date_str: str) -> dict:
    if not date_str:
        return {"valid": False, "reason": "empty"}
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            datetime.strptime(date_str.strip(), fmt)
            return {"valid": True, "reason": None}
        except ValueError:
            continue
    return {"valid": False, "reason": "unknown format"}