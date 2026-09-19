class ValidationService:
    def validate(self, fields: dict) -> dict:
        errors = []
        if not fields.get("nin"):
            errors.append("NIN manquant")
        if not fields.get("nom"):
            errors.append("Nom manquant")
        return {"valid": not errors, "errors": errors}