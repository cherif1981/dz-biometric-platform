def validate_document(fields: dict) -> dict:
    """Aggregate validation of all fields."""
    errors = []
    if not fields.get("nin"):
        errors.append("NIN manquant")
    if not fields.get("nom"):
        errors.append("Nom manquant")
    if not fields.get("prenom"):
        errors.append("Prénom manquant")
    return {"valid": len(errors) == 0, "errors": errors}