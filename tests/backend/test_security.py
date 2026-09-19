from datetime import timedelta

from jose import jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify():
    h = hash_password("secret123")
    assert h != "secret123"
    assert verify_password("secret123", h)
    assert not verify_password("wrong", h)


def test_create_access_token():
    token = create_access_token({"sub": "a@b.c"})
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    assert payload["sub"] == "a@b.c"
    assert "exp" in payload


def test_create_access_token_custom_expiry():
    token = create_access_token({"sub": "a@b.c"}, expires_delta=timedelta(seconds=5))
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    assert "exp" in payload