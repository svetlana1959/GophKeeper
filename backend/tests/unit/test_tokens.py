import pytest

from gophkeeper.security import tokens

_SECRET = b"unit-test-secret"


def test_sign_verify_roundtrip():
    token = tokens.sign({"typ": "session", "did": "abc"}, secret=_SECRET, ttl_seconds=60)
    payload = tokens.verify(token, secret=_SECRET)
    assert payload["typ"] == "session"
    assert payload["did"] == "abc"
    assert "exp" in payload


def test_verify_rejects_wrong_secret():
    token = tokens.sign({"x": 1}, secret=_SECRET, ttl_seconds=60)
    with pytest.raises(tokens.TokenError):
        tokens.verify(token, secret=b"other-secret")


def test_verify_rejects_tampered_payload():
    token = tokens.sign({"role": "device"}, secret=_SECRET, ttl_seconds=60)
    encoded, signature = token.split(".", 1)
    tampered = tokens._b64e(b'{"role":"admin","exp":9999999999}') + "." + signature
    with pytest.raises(tokens.TokenError):
        tokens.verify(tampered, secret=_SECRET)


def test_verify_rejects_expired():
    token = tokens.sign({"x": 1}, secret=_SECRET, ttl_seconds=-1)
    with pytest.raises(tokens.TokenError):
        tokens.verify(token, secret=_SECRET)


def test_verify_rejects_malformed():
    with pytest.raises(tokens.TokenError):
        tokens.verify("not-a-token", secret=_SECRET)
