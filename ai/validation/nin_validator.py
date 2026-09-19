import re


def validate_nin(nin: str) -> dict:
    """Validate Algerian NIN (18 digits)."""
    if not nin:
        return {"valid": False, "reason": "empty"}
    nin = nin.strip().replace(" ", "")
    if not re.fullmatch(r"\d{18}", nin):
        return {"valid": False, "reason": "must be 18 digits"}
    return {"valid": True, "reason": None}