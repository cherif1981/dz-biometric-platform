"""Biometric data protection: encryption, redaction."""
import base64
import os
import pytest


# --- Encryption tests ---

def test_encrypt_decrypt_roundtrip():
    from src.core.biometric_crypto import encrypt_biometric, decrypt_biometric, generate_key_b64
    os.environ["BIOMETRIC_ENC_KEY"] = generate_key_b64()
    import importlib
    import src.core.biometric_crypto as bc
    importlib.reload(bc)

    plaintext = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
    stored = bc.encrypt_biometric(plaintext)
    assert bc.is_encrypted(stored)
    assert not stored.startswith("PLAINTEXT::")
    assert bc.decrypt_biometric(stored) == plaintext


def test_encryption_uses_random_nonce():
    from src.core.biometric_crypto import generate_key_b64
    os.environ["BIOMETRIC_ENC_KEY"] = generate_key_b64()
    import importlib
    import src.core.biometric_crypto as bc
    importlib.reload(bc)

    a = bc.encrypt_biometric(b"same-bytes")
    b = bc.encrypt_biometric(b"same-bytes")
    assert a != b


def test_encryption_tamper_detected():
    from src.core.biometric_crypto import generate_key_b64
    os.environ["BIOMETRIC_ENC_KEY"] = generate_key_b64()
    import importlib
    import src.core.biometric_crypto as bc
    importlib.reload(bc)

    stored = bc.encrypt_biometric(b"tamper-me")
    raw = base64.b64decode(stored)
    tampered = base64.b64encode(raw[:-1] + bytes([raw[-1] ^ 0xFF])).decode()
    with pytest.raises(Exception):
        bc.decrypt_biometric(tampered)


def test_missing_key_falls_back_with_marker():
    os.environ.pop("BIOMETRIC_ENC_KEY", None)
    import importlib
    import src.core.biometric_crypto as bc
    importlib.reload(bc)

    stored = bc.encrypt_biometric(b"dev-only")
    assert stored.startswith("PLAINTEXT::")


# --- Redaction tests ---

def test_mask_subject_is_stable_and_short():
    from src.core.log_redaction import mask_subject
    m1 = mask_subject("user@example.com")
    m2 = mask_subject("user@example.com")
    assert m1 == m2
    assert m1.startswith("<subject:") and m1.endswith(">")
    assert len(m1) < 20
    assert "user@example.com" not in m1


def test_redact_strips_hex_and_b64():
    from src.core.log_redaction import redact_message
    msg = "processing image=" + "a" * 64 + " hash=" + base64.b64encode(b"x" * 100).decode()
    out = redact_message(msg)
    assert "aaaa" not in out
    assert "<REDACTED_HEX>" in out or "<REDACTED_B64>" in out
    assert base64.b64encode(b"x" * 100).decode() not in out


def test_redact_removes_jpeg_magic():
    from src.core.log_redaction import redact_message
    msg = "payload=b'\xff\xd8\xff\xe0...'"
    out = redact_message(msg)
    assert "\xff\xd8\xff" not in out
    assert "<REDACTED_JPEG>" in out
