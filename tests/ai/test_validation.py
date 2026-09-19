from validation.nin_validator import validate_nin
from validation.date_validator import validate_date
from validation.document_validator import validate_document


def test_nin_valid():
    assert validate_nin("123456789012345678")["valid"] is True


def test_nin_invalid_length():
    assert validate_nin("123")["valid"] is False


def test_nin_empty():
    assert validate_nin("")["valid"] is False


def test_date_valid_formats():
    assert validate_date("01/01/1990")["valid"] is True
    assert validate_date("01-01-1990")["valid"] is True
    assert validate_date("01.01.1990")["valid"] is True


def test_date_invalid():
    assert validate_date("32/13/1990")["valid"] is False
    assert validate_date("")["valid"] is False


def test_document_valid():
    r = validate_document({"nin": "1", "nom": "A", "prenom": "B"})
    assert r["valid"] is True


def test_document_missing_fields():
    r = validate_document({"nin": None, "nom": None, "prenom": None})
    assert r["valid"] is False
    assert len(r["errors"]) >= 3