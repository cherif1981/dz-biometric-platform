"""SEC-04: encryption key handling."""
import os
import pytest


def test_encrypt_decrypt_roundtrip(monkeypatch):
    from cryptography.fernet import Fernet
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("ENVIRONMENT", "development")

    from importlib import reload
    import src.core.config as cfg
    reload(cfg)
    import src.core.field_encryption as fe
    reload(fe)

    token = fe.encrypt_field("NIN-123456")
    assert token != "NIN-123456"
    assert fe.decrypt_field(token) == "NIN-123456"


def test_tampered_ciphertext_rejected(monkeypatch):
    from cryptography.fernet import Fernet
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("ENVIRONMENT", "development")

    from importlib import reload
    import src.core.config as cfg
    reload(cfg)
    import src.core.field_encryption as fe
    reload(fe)

    token = fe.encrypt_field("hello")
    tampered = token[:-4] + "XXXX"
    with pytest.raises(ValueError):
        fe.decrypt_field(tampered)


def test_production_missing_key_raises(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", "")
    monkeypatch.setenv("SECRET_KEY", "x" * 40)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")

    from importlib import reload
    import src.core.config as cfg
    reload(cfg)
    import src.core.field_encryption as fe
    reload(fe)

    with pytest.raises(fe.EncryptionKeyMissing):
        fe._fernet.cache_clear()
        fe._fernet()


def test_rotate_key(monkeypatch):
    from cryptography.fernet import Fernet
    old_key = Fernet.generate_key().decode()
    new_key = Fernet.generate_key().decode()
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", old_key)
    monkeypatch.setenv("ENVIRONMENT", "development")

    from importlib import reload
    import src.core.config as cfg
    reload(cfg)
    import src.core.field_encryption as fe
    reload(fe)

    token_old = fe.encrypt_field("secret-data")
    token_new = fe.rotate_key(new_key, token_old)

    # Verify new token decrypts with new key
    from cryptography.fernet import Fernet
    plain = Fernet(new_key.encode()).decrypt(token_new.encode()).decode()
    assert plain == "secret-data"
