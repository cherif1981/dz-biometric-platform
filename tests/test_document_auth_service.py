"""Document auth service tests — MRZ checksums + fail-closed liveness."""
import pytest
from src.services.document_auth_service import (
    mrz_checksum, validate_td3_mrz, validate_td1_mrz,
    find_mrz_lines, DocumentAuthService, RecaptureDetector,
)


# ═══ Checksum algorithm ══════════════════════════════════════════════
class TestMRZChecksum:
    def test_known_td3_line2_checks(self):
        # Verify against hand-computed ICAO 9303 values:
        # 520727 → 5*7+2*3+0*1+7*7+2*3+7*1 = 35+6+0+49+6+7 = 103 → 3
        assert mrz_checksum("520727") == 3
        # 160428 → 1*7+6*3+0*1+4*7+2*3+8*1 = 7+18+0+28+6+8 = 67 → 7
        assert mrz_checksum("160428") == 7

    def test_all_zeros(self):
        assert mrz_checksum("000000") == 0

    def test_all_letters_A(self):
        # A=10; 10*7 + 10*3 + 10*1 = 110 → 0
        assert mrz_checksum("AAA") == 0

    def test_filler_char(self):
        assert mrz_checksum("<<<") == 0

    def test_invalid_char_raises(self):
        with pytest.raises(ValueError):
            mrz_checksum("A!B")


# ═══ Correct MRZ constructors ════════════════════════════════════════
def _make_td3_line2(doc_no="L898902C3", dob="740812", exp="120415",
                    pers="ZE184226B<<<<<", sex="M", nat="DZA"):
    """Build a valid 44-char TD3 line 2 per ICAO 9303 layout.

    [0:9]=doc_no  [9]=check  [10:13]=nat  [13:19]=dob  [19]=check
    [20]=sex  [21:27]=exp  [27]=check  [28:42]=pers  [42]=check
    [43]=composite check
    """
    doc_chk = mrz_checksum(doc_no)
    dob_chk = mrz_checksum(dob)
    exp_chk = mrz_checksum(exp)
    pers_chk = mrz_checksum(pers)
    line43 = (doc_no + str(doc_chk) + nat + dob + str(dob_chk) + sex +
              exp + str(exp_chk) + pers + str(pers_chk))
    assert len(line43) == 43, f"expected 43 chars, got {len(line43)}: {line43!r}"
    comp_field = line43[0:10] + line43[13:20] + line43[21:28] + line43[28:43]
    comp = mrz_checksum(comp_field)
    line2 = line43 + str(comp)
    assert len(line2) == 44, f"expected 44 chars, got {len(line2)}"
    return line2


def _make_td3_line1():
    """Minimal 44-char TD3 line 1 (only length/shape matters)."""
    return "P<DZA" + "<" * 39


def _make_td1_lines(doc_no="D23145890", dob="740812", exp="120415",
                    nat="DZA", opt2="<<<<<<<<<<<"):
    """Build valid 30-char TD1 line1 + line2 per ICAO 9303."""
    doc_chk = mrz_checksum(doc_no)
    dob_chk = mrz_checksum(dob)
    exp_chk = mrz_checksum(exp)
    opt2_chk = mrz_checksum(opt2)
    # line1: [0:5]=doc code+filler, [5:14]=doc_no, [14]=check, [15:30]=opt1
    line1 = ("ID<<<" + doc_no + str(doc_chk)).ljust(30, "<")
    # line2: [0:6]=dob, [6]=check, [7]=sex, [8:14]=exp, [14]=check,
    #        [15:18]=nat, [18:29]=opt2, [29]=check
    line2 = (dob + str(dob_chk) + "M" + exp + str(exp_chk)
             + nat + opt2 + str(opt2_chk))
    assert len(line1) == 30, f"line1 length {len(line1)}"
    assert len(line2) == 30, f"line2 length {len(line2)}: {line2!r}"
    return line1, line2


def _passport_mrz_pair():
    return _make_td3_line1() + "\n" + _make_td3_line2()


# ═══ TD3 (passport) ══════════════════════════════════════════════════
class TestTD3:
    def test_valid_line_passes(self):
        r = validate_td3_mrz(_make_td3_line2())
        assert r.valid, f"errors: {r.errors}"
        assert r.fields["document_number"] == "L898902C3"
        assert r.fields["date_of_birth"] == "740812"
        assert r.fields["nationality"] == "DZA"

    def test_flipped_doc_no_check_fails(self):
        chars = list(_make_td3_line2())
        chars[9] = "0" if chars[9] != "0" else "1"
        r = validate_td3_mrz("".join(chars))
        assert not r.valid
        assert any("doc_no" in e for e in r.errors)

    def test_flipped_dob_check_fails(self):
        chars = list(_make_td3_line2())
        chars[19] = "0" if chars[19] != "0" else "1"
        r = validate_td3_mrz("".join(chars))
        assert not r.valid
        assert any("dob" in e for e in r.errors)

    def test_wrong_length_fails(self):
        r = validate_td3_mrz("TOO_SHORT")
        assert not r.valid
        assert any("length" in e for e in r.errors)


# ═══ TD1 (ID card) ═══════════════════════════════════════════════════
class TestTD1:
    def test_valid_card_passes(self):
        l1, l2 = _make_td1_lines()
        r = validate_td1_mrz(l1, l2)
        assert r.valid, f"errors: {r.errors}"
        assert r.fields["document_number"] == "D23145890"
        assert r.fields["nationality"] == "DZA"


# ═══ MRZ line detection ══════════════════════════════════════════════
class TestMRZDetection:
    def test_detects_44char_line(self):
        line = _make_td3_line2()
        found = find_mrz_lines("Some header\n" + line + "\nfooter")
        assert len(found) == 1
        assert found[0] == line

    def test_detects_two_lines(self):
        found = find_mrz_lines(_passport_mrz_pair())
        assert len(found) == 2

    def test_ignores_short_text(self):
        assert find_mrz_lines("hello world") == []

    def test_empty_input(self):
        assert find_mrz_lines("") == []


# ═══ Recapture liveness (fail-closed) ════════════════════════════════
class TestRecapture:
    def test_no_predictor_returns_zero(self):
        assert RecaptureDetector().predict(None) == 0.0

    def test_predictor_used_when_set(self):
        d = RecaptureDetector(); d.set_predictor(lambda _: 0.87)
        assert d.predict("dummy") == pytest.approx(0.87)

    def test_predictor_exception_returns_zero(self):
        d = RecaptureDetector(); d.set_predictor(lambda _: 1 / 0)
        assert d.predict("x") == 0.0

    def test_predictor_out_of_range_clamped(self):
        d = RecaptureDetector(); d.set_predictor(lambda _: 1.5)
        assert d.predict("x") == 1.0
        d.set_predictor(lambda _: -0.5)
        assert d.predict("x") == 0.0


# ═══ Service integration ═════════════════════════════════════════════
class TestService:
    def test_valid_passport_with_liveness(self):
        det = RecaptureDetector(); det.set_predictor(lambda _: 0.9)
        svc = DocumentAuthService(recapture_detector=det)
        r = svc.validate(_passport_mrz_pair(), image_or_frames="img")
        assert r.mrz_valid, f"reasons: {r.reasons}"
        assert r.document_authentic
        assert r.liveness_score == pytest.approx(0.9)

    def test_no_liveness_blocks_authentic(self):
        svc = DocumentAuthService()  # default detector returns 0.0
        r = svc.validate(_passport_mrz_pair(), image_or_frames="img")
        assert r.mrz_valid
        assert not r.document_authentic
        assert "document_not_live" in r.reasons

    def test_forged_mrz_blocks_authentic(self):
        det = RecaptureDetector(); det.set_predictor(lambda _: 0.99)
        svc = DocumentAuthService(recapture_detector=det)
        lines = _passport_mrz_pair().split("\n")
        corrupted = list(lines[1])
        corrupted[9] = "0" if corrupted[9] != "0" else "1"
        bad = lines[0] + "\n" + "".join(corrupted)
        r = svc.validate(bad, image_or_frames="img")
        assert not r.mrz_valid
        assert not r.document_authentic

    def test_no_mrz_evidence_reports_unknown(self):
        svc = DocumentAuthService()
        r = svc.validate("random text", image_or_frames=None)
        assert not r.mrz_valid
        assert r.doc_type == "unknown"
        assert any("mrz" in x for x in r.reasons)


# ═══ FORCE_REVIEW invariant ══════════════════════════════════════════
class TestAuthCannotBypassForceReview:
    def test_perfect_document_still_reviewed_under_policy(self):
        from anti_spoof.decision import POLICY, PADState, Decision, decide
        if POLICY != "FORCE_REVIEW":
            pytest.skip("policy not active")
        assert decide(0.99, PADState.VERIFIED) == Decision.REVIEW
