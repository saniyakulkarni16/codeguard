import jwt
import pytest

from codeguard import config
from codeguard.security import create_access_token, hash_password, verify_password


def test_password_hash_and_verify():
    h = hash_password("correct horse battery")
    assert h != "correct horse battery"
    assert verify_password("correct horse battery", h)
    assert not verify_password("wrong password", h)


def test_long_and_unicode_passwords_work():
    pw = "pässwörd-" * 40  # far beyond bcrypt's 72-byte limit
    assert verify_password(pw, hash_password(pw))
    assert not verify_password(pw[:-1], hash_password(pw))


def test_token_roundtrip():
    tok = create_access_token(42)
    payload = jwt.decode(tok, config.SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
    assert payload["sub"] == "42"


def test_expired_token_is_rejected(monkeypatch):
    monkeypatch.setattr(config, "ACCESS_TOKEN_MINUTES", -1)
    tok = create_access_token(1)
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(tok, config.SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
