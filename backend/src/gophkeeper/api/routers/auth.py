"""Authentication endpoints — the age challenge/response handshake."""

import base64
import binascii

from fastapi import APIRouter, Depends

from gophkeeper.api.deps import get_principal, provide
from gophkeeper.api.schemas.auth import (
    ChallengeRequest,
    ChallengeResponse,
    SessionResponse,
    VerifyRequest,
    WhoAmIResponse,
)
from gophkeeper.domain.errors import AuthenticationError
from gophkeeper.security.principal import DevicePrincipal
from gophkeeper.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


_UNAUTHORIZED = {401: {"description": "Unknown/revoked device, or a bad/expired token."}}


@router.post(
    "/challenge",
    response_model=ChallengeResponse,
    summary="Request a login challenge",
    responses=_UNAUTHORIZED,
)
async def challenge(
    body: ChallengeRequest,
    service: AuthService = Depends(provide(AuthService)),
) -> ChallengeResponse:
    """Start the age challenge for a registered device.

    The server encrypts a random nonce **to the device's public key** and returns
    it (base64) alongside a short-lived `challenge_token` that binds the device
    and the nonce. The device decrypts the challenge with its private key and
    answers via `/auth/verify`.
    """
    ciphertext, token = await service.challenge(public_key=body.public_key)
    return ChallengeResponse(
        challenge=base64.b64encode(ciphertext).decode("ascii"),
        challenge_token=token,
    )


@router.post(
    "/verify",
    response_model=SessionResponse,
    summary="Complete login, receive a session token",
    responses=_UNAUTHORIZED,
)
async def verify(
    body: VerifyRequest,
    service: AuthService = Depends(provide(AuthService)),
) -> SessionResponse:
    """Submit the decrypted nonce to finish the challenge.

    On success the server returns a bearer `access_token` to send as
    `Authorization: Bearer <token>` on subsequent calls.
    """
    try:
        nonce = base64.b64decode(body.nonce, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise AuthenticationError("malformed nonce") from exc
    access_token, expires_in = await service.verify(
        challenge_token=body.challenge_token, nonce=nonce
    )
    return SessionResponse(access_token=access_token, expires_in=expires_in)


@router.get(
    "/whoami",
    response_model=WhoAmIResponse,
    summary="Identify the current session",
    responses=_UNAUTHORIZED,
)
async def whoami(
    principal: DevicePrincipal = Depends(get_principal),
) -> WhoAmIResponse:
    """Return the device and account the bearer token authenticates."""
    return WhoAmIResponse(device_id=principal.device_id, account_id=principal.account_id)
