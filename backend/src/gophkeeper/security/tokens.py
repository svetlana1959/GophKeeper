"""Compact HMAC-signed tokens.

Two uses, both stateless: the short-lived *challenge* token that carries a login
challenge's bound data, and the *session* token issued after a device proves key
possession. Stateless means no server-side challenge/session table — the
signature is the integrity guarantee and ``exp`` the expiry.

Format: ``base64url(json_payload).base64url(hmac_sha256(payload))``. Small,
URL-safe, and dependency-free (stdlib only).
"""

import base64
import binascii
import hashlib
import hmac
import json
import time


class TokenError(Exception):
    """The token is malformed, has a bad signature, or has expired."""


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64d(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def sign(payload: dict, *, secret: bytes, ttl_seconds: int) -> str:
    """Serialize and sign ``payload``, stamping an expiry ``ttl_seconds`` ahead."""
    body = {**payload, "exp": int(time.time()) + ttl_seconds}
    encoded = _b64e(json.dumps(body, separators=(",", ":"), sort_keys=True).encode())
    signature = hmac.new(secret, encoded.encode("ascii"), hashlib.sha256).digest()
    return f"{encoded}.{_b64e(signature)}"


def verify(token: str, *, secret: bytes) -> dict:
    """Verify signature and expiry, returning the payload. Raises ``TokenError``."""
    try:
        encoded, signature = token.split(".", 1)
    except ValueError as exc:
        raise TokenError("malformed token") from exc

    expected = hmac.new(secret, encoded.encode("ascii"), hashlib.sha256).digest()
    try:
        provided = _b64d(signature)
    except (ValueError, binascii.Error) as exc:
        raise TokenError("malformed signature") from exc
    if not hmac.compare_digest(expected, provided):
        raise TokenError("bad signature")

    payload = json.loads(_b64d(encoded))
    if payload.get("exp", 0) < int(time.time()):
        raise TokenError("expired")
    return payload
