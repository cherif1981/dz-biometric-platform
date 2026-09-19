import pytest

from app.services.validation_service import ValidationService


def test_validation_service_valid():
    svc = ValidationService()
    r = svc.validate({"nin": "1", "nom": "A", "prenom": "B"})
    assert r["valid"] is True
    assert r["errors"] == []


def test_validation_service_invalid():
    svc = ValidationService()
    r = svc.validate({"nin": None, "nom": None, "prenom": None})
    assert r["valid"] is False
    assert len(r["errors"]) >= 2