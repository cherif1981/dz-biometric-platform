from src.modules.encryption.field_encryption import FieldEncryptor


def test_roundtrip():
    e = FieldEncryptor()
    ct = e.encrypt("NIN-123456789012345678")
    assert ct != "NIN-123456789012345678"
    assert e.decrypt(ct) == "NIN-123456789012345678"


def test_none_safe():
    e = FieldEncryptor()
    assert e.encrypt(None) is None
    assert e.decrypt(None) is None