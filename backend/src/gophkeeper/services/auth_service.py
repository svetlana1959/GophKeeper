"""Application service for device authentication.

A device proves it holds its private key without ever sending it:

  1. challenge() — the server encrypts a random nonce *to* the device's age
     public key and returns it alongside a short-lived, signed challenge token
     that binds the device and the nonce's hash.
  2. verify() — the device returns the decrypted nonce; the server checks it
     against the token and issues a session token.

Both tokens are stateless (HMAC-signed), so there is no challenge/session table.
"""

import hashlib
import secrets as randbytes
from uuid import UUID

from gophkeeper.domain.errors import AuthenticationError, DeviceNotFound
from gophkeeper.domain.unit_of_work import UnitOfWork
from gophkeeper.security import age, tokens
from gophkeeper.security.principal import DevicePrincipal
from gophkeeper.settings.settings import settings

_NONCE_BYTES = 32
_CHALLENGE_TYP = "challenge"
_SESSION_TYP = "session"


class AuthService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    @property
    def _secret(self) -> bytes:
        return settings.security.secret_key.encode()

    async def challenge(self, *, public_key: str) -> tuple[bytes, str]:
        """Return (age-encrypted nonce, challenge token) for a known device."""
        async with self._uow as uow:
            device = await uow.devices.find_by_public_key(public_key)
        if device is None or not device.may_authenticate():
            raise AuthenticationError("unknown device")

        nonce = randbytes.token_bytes(_NONCE_BYTES)
        try:
            ciphertext = age.encrypt_to(public_key, nonce)
        except age.InvalidPublicKey as exc:
            raise AuthenticationError("invalid public key") from exc

        token = tokens.sign(
            {
                "typ": _CHALLENGE_TYP,
                "did": str(device.id),
                "aid": str(device.account_id),
                "nonce_hash": hashlib.sha256(nonce).hexdigest(),
            },
            secret=self._secret,
            ttl_seconds=settings.security.challenge_ttl_seconds,
        )
        return ciphertext, token

    async def verify(self, *, challenge_token: str, nonce: bytes) -> tuple[str, int]:
        """Validate a challenge answer, returning (session token, ttl seconds)."""
        payload = self._decode(challenge_token, expected=_CHALLENGE_TYP)
        if hashlib.sha256(nonce).hexdigest() != payload.get("nonce_hash"):
            raise AuthenticationError("challenge response did not match")

        device_id = UUID(payload["did"])
        async with self._uow as uow:
            try:
                device = await uow.devices.get(device_id)
            except DeviceNotFound as exc:
                raise AuthenticationError("unknown device") from exc
            if not device.may_authenticate():
                raise AuthenticationError("device is not active")
            device.touch()
            await uow.devices.save(device)
            await uow.commit()

        ttl = settings.security.session_ttl_seconds
        session = tokens.sign(
            {"typ": _SESSION_TYP, "did": payload["did"], "aid": payload["aid"]},
            secret=self._secret,
            ttl_seconds=ttl,
        )
        return session, ttl

    async def principal(self, token: str) -> DevicePrincipal:
        """Resolve a bearer session token to its authenticated device.

        Re-checks the device's lifecycle on every request (one indexed read):
        a valid signature is not enough, the device must still be allowed to
        authenticate. This is what makes revocation take effect immediately
        rather than lingering until the stateless token's TTL expires.
        """
        payload = self._decode(token, expected=_SESSION_TYP)
        device_id = UUID(payload["did"])
        async with self._uow as uow:
            try:
                device = await uow.devices.get(device_id)
            except DeviceNotFound as exc:
                raise AuthenticationError("unknown device") from exc
        if not device.may_authenticate():
            raise AuthenticationError("device is not active")
        return DevicePrincipal(device_id=device.id, account_id=device.account_id)

    def _decode(self, token: str, *, expected: str) -> dict:
        try:
            payload = tokens.verify(token, secret=self._secret)
        except tokens.TokenError as exc:
            raise AuthenticationError(str(exc)) from exc
        if payload.get("typ") != expected:
            raise AuthenticationError(f"expected a {expected} token")
        return payload
