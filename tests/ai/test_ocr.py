from ocr.parser import parse_fields
from ocr.postprocessing import clean_text


def test_parse_fields_nin():
    text = "Nom: BENALI\nPrenom: Ahmed\n123456789012345678\n01/01/1990"
    r = parse_fields(text)
    assert r["nin"] == "123456789012345678"
    assert r["nom"] == "BENALI"
    assert r["prenom"] == "Ahmed"
    assert r["date_naissance"] == "01/01/1990"


def test_parse_fields_empty():
    r = parse_fields("")
    assert r["nin"] is None
    assert r["nom"] is None


def test_clean_text_collapses_spaces():
    assert clean_text("a   b\n\nc") == "a b c"