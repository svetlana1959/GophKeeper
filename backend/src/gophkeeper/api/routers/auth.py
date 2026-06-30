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


@router.post("/challenge", response_model=ChallengeResponse)
async def challenge(
    body: ChallengeRequest,
    service: AuthService = Depends(provide(AuthService)),
) -> ChallengeResponse:
    ciphertext, token = await service.challenge(public_key=body.public_key)
    return ChallengeResponse(
        challenge=base64.b64encode(ciphertext).decode("ascii"),
        challenge_token=token,
    )


@router.post("/verify", response_model=SessionResponse)
async def verify(
    body: VerifyRequest,
    service: AuthService = Depends(provide(AuthService)),
) -> SessionResponse:
    try:
        nonce = base64.b64decode(body.nonce, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise AuthenticationError("malformed nonce") from exc
    access_token, expires_in = await service.verify(
        challenge_token=body.challenge_token, nonce=nonce
    )
    return SessionResponse(access_token=access_token, expires_in=expires_in)


@router.get("/whoami", response_model=WhoAmIResponse)
async def whoami(
    principal: DevicePrincipal = Depends(get_principal),
) -> WhoAmIResponse:
    return WhoAmIResponse(device_id=principal.device_id, account_id=principal.account_id)
