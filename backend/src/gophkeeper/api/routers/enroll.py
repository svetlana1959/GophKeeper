"""Enrollment endpoints — invite a device, join with a code."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from gophkeeper.api.deps import get_account_id, provide
from gophkeeper.api.schemas.device import DeviceResponse
from gophkeeper.api.schemas.enroll import CreateInviteResponse, JoinRequest
from gophkeeper.services.enrollment_service import EnrollmentService

router = APIRouter(prefix="/enroll", tags=["enroll"])


@router.post(
    "/invite",
    response_model=CreateInviteResponse,
    summary="Create a pairing invite",
    responses={401: {"description": "Missing, invalid, or expired bearer token."}},
)
async def create_invite(
    account_id: UUID = Depends(get_account_id),
    service: EnrollmentService = Depends(provide(EnrollmentService)),
) -> CreateInviteResponse:
    """Mint a single-use, expiring code for a new device to join this account.

    Callable by a logged-in **web session** (the webapp linking a CLI device) or
    by an already-linked **device**. The plaintext code is returned **once**
    (only its hash is stored); the new device calls `/enroll/join`.
    """
    invite, code = await service.create_invite(account_id=account_id)
    return CreateInviteResponse(code=code, expires_at=invite.expires_at)


@router.post(
    "/join",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Join an account with an invite code",
    responses={
        400: {"description": "Unknown, already-used, or expired invite code."},
        409: {"description": "This public key is already registered."},
    },
)
async def join(
    body: JoinRequest,
    service: EnrollmentService = Depends(provide(EnrollmentService)),
) -> DeviceResponse:
    """Admit a new device into the invite's account, consuming the invite.

    Unauthenticated — the code is the authorization. The device becomes active
    immediately; a key-holding device reshares the account's secrets to it on its
    next sync.
    """
    device = await service.join(
        code=body.code,
        device_name=body.device_name,
        public_key=body.public_key,
    )
    return DeviceResponse.from_domain(device)
