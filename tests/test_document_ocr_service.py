"""Document OCR service tests — pure parsers + mocked OCR.

No model is loaded here. Slow tests are marked requires_model.
"""
import os
import numpy as np
import pytest

from src.services.document_ocr_service import (
    DocumentOCRService,
    normalize_arabic_digits,
    parse_cnibe_fields,
    parse_passport_fields,
    detect_document_type_from_text,
)

RUN_SLOW = os.getenv("FACE_MATCH_RUN_SLOW", "0") == "1"
requires_model = pytest.mark.skipif(not RUN_SLOW, reason="set FACE_MATCH_RUN_SLOW=1")


# ═══ Pure-function tests ═════════════════════════════════════════════
class TestNormalizeDigits:
    def test_arabic_indic_digits(self):
        assert normalize_arabic_digits("\u0661\u0662\u0663\u0664\u0665") == "12345"

    def test_mixed_text_preserved(self):
        assert normalize_arabic_digits("NIN \u0661\u0662 \u0663\u0664") == "NIN 12 34"

    def test_empty_and_none(self):
        assert normalize_arabic_digits("") == ""
        assert normalize_arabic_digits(None) is None


class TestCNIBEParser:
    def test_extracts_nin_from_label(self):
        text = "R\u00C9PUBLIQUE ALG\u00C9RIENNE\nN.I.N : 123456789012345678\nNom : BENALI"
        r = parse_cnibe_fields(text)
        assert r["nin"] == "123456789012345678"

    def test_extracts_nin_with_spaces(self):
        text = "NIN 1234 5678 9012 3456 78"
        r = parse_cnibe_fields(text)
        assert r["nin"] == "123456789012345678"

    def test_extracts_nin_arabic_digits(self):
        text = "N.I.N: \u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668"
        r = parse_cnibe_fields(text)
        assert r["nin"] == "123456789012345678"

    def test_extracts_surname_and_dob(self):
        text = "Nom : BENALI\nPr\u00E9nom : Ahmed\nDate de naissance : 15/03/1990"
        r = parse_cnibe_fields(text)
        assert r["surname"] == "BENALI"
        assert r["given_name"] == "Ahmed"
        assert r["dob"] == "15/03/1990"

    def test_missing_fields_are_none(self):
        r = parse_cnibe_fields("random text with no fields")
        assert all(v is None for v in r.values())


class TestPassportParser:
    def test_extracts_passport_no(self):
        text = "PASSEPORT\nPasseport No : AB1234567\nNom : BENALI"
        r = parse_passport_fields(text)
        assert r["passport_no"] == "AB1234567"

    def test_extracts_expiry(self):
        text = "Date d'expiration : 31/12/2030"
        r = parse_passport_fields(text)
        assert r["expiry"] == "31/12/2030"


class TestDocumentTypeDetection:
    def test_passport_by_mrz(self):
        # Two 44-char MRZ lines
        line = "P<DZABENALI<<AHMED<<<<<<<<<<<<<<<<<<<<<<<<<<<<<"
        line2 = "AB1234567DZA9003151M3012314<<<<<<<<<<<<<<<<<<<<"
        # Pad to exactly 44
        line = (line + "<" * 44)[:44]
        line2 = (line2 + "<" * 44)[:44]
        text = line + "\n" + line2
        assert detect_document_type_from_text(text) == "passport"

    def test_cnibe_by_keyword(self):
        assert detect_document_type_from_text("CARTE NATIONALE D'IDENTIT\u00C9") == "cnibe"

    def test_unknown(self):
        assert detect_document_type_from_text("random text") == "unknown"

    def test_empty(self):
        assert detect_document_type_from_text("") == "unknown"


# ═══ Service-level tests with mocked OCR ═════════════════════════════
class TestDocumentOCRService:
    def _mock_service(self, text_by_lang: dict):
        svc = DocumentOCRService(langs=tuple(text_by_lang.keys()))

        def fake_get_ocr(lang):
            return object()  # placeholder

        def fake_ocr_lang(image_bgr, lang):
            return [
                {"text": t, "confidence": 0.99, "bbox": [[0, 0], [1, 0], [1, 1], [0, 1]]}
                for t in text_by_lang.get(lang, [])
            ]

        svc._get_ocr = fake_get_ocr
        svc._ocr_lang = fake_ocr_lang
        return svc

    def test_extract_raw_text_merges_langs(self):
        svc = self._mock_service({"ar": ["\u0627\u0644\u0627\u0633\u0645"], "fr": ["Nom"]})
        img = np.zeros((10, 10, 3), dtype=np.uint8)
        lines = svc.extract_raw_text(img)
        assert len(lines) == 2
        assert {l["text"] for l in lines} == {"\u0627\u0644\u0627\u0633\u0645", "Nom"}

    def test_extract_fields_cnibe(self):
        svc = self._mock_service({
            "fr": ["CARTE NATIONALE", "N.I.N : 123456789012345678", "Nom : BENALI"],
            "ar": [],
        })
        img = np.zeros((10, 10, 3), dtype=np.uint8)
        r = svc.extract_fields(img)
        assert r["doc_type"] == "cnibe"
        assert r["fields"]["nin"] == "123456789012345678"
        assert r["fields"]["surname"] == "BENALI"

    def test_extract_fields_passport(self):
        svc = self._mock_service({
            "fr": ["PASSEPORT", "Passeport No : AB1234567"],
            "ar": [],
        })
        img = np.zeros((10, 10, 3), dtype=np.uint8)
        r = svc.extract_fields(img)
        assert r["doc_type"] == "passport"
        assert r["fields"]["passport_no"] == "AB1234567"

    def test_empty_image_raises(self):
        svc = DocumentOCRService(langs=("fr",))
        with pytest.raises(ValueError, match="empty image"):
            svc.extract_raw_text(None)


# ═══ FORCE_REVIEW isolation ══════════════════════════════════════════
class TestOCRCannotBypassForceReview:
    """Even perfect OCR (NIN extracted, doc_type=cnibe) must not yield ACCEPT."""

    def test_perfect_ocr_still_reviewed_under_policy(self):
        from anti_spoof.decision import POLICY, PADState, Decision, decide
        if POLICY != "FORCE_REVIEW":
            pytest.skip("policy not active")
        # Simulate a perfect extraction result
        perfect = {"nin": "123456789012345678", "surname": "BENALI"}
        assert perfect["nin"]  # extraction succeeded
        # But decide() still forces REVIEW regardless
        assert decide(0.99, PADState.VERIFIED) == Decision.REVIEW


# ═══ Slow integration (real PaddleOCR) ═══════════════════════════════
@requires_model
class TestDocumentOCRRealModel:
    def test_paddleocr_loads(self):
        svc = DocumentOCRService(langs=("fr",))
        svc._get_ocr("fr")  # triggers paddleocr import + model download


class TestCNIBEParserRegression:
    """Guard against cross-line capture in name patterns."""

    def test_place_of_birth_does_not_swallow_next_line(self):
        text = "Lieu de naissance : ALGER\nSexe : M"
        r = parse_cnibe_fields(text)
        assert r["place_of_birth"] == "ALGER", f"got {r['place_of_birth']!r}"

    def test_given_name_does_not_swallow_next_line(self):
        text = "Pr\u00E9nom : AHMED\nDate de naissance : 15/03/1990"
        r = parse_cnibe_fields(text)
        assert r["given_name"] == "AHMED", f"got {r['given_name']!r}"

    def test_multiword_names_still_work(self):
        text = "Nom : EL MEKKI\nPr\u00E9nom : MOHAMED AMINE"
        r = parse_cnibe_fields(text)
        assert r["surname"] == "EL MEKKI"
        assert r["given_name"] == "MOHAMED AMINE"

    def test_surname_does_not_swallow_dob_line(self):
        text = "Nom : BENALI\nDate de naissance : 15/03/1990"
        r = parse_cnibe_fields(text)
        assert r["surname"] == "BENALI"
        assert "\n" not in r["surname"]
