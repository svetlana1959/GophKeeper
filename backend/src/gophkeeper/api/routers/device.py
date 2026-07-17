"""Devices endpoints.

Devices are read-only here: they are created by joining an account with an
invite (`/enroll/join`), never by the CLI bootstrapping an account. Account
creation lives on the web (`/accounts`).
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from gophkeeper.api.deps import get_account_id, get_principal, provide
from gophkeeper.api.schemas.device import DeviceResponse, HeartbeatRequest
from gophkeeper.security.principal import DevicePrincipal
from gophkeeper.services.device_service import DeviceService

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get(
    "",
    response_model=list[DeviceResponse],
    summary="List the account's devices",
    responses={401: {"description": "Missing, invalid, or expired bearer token."}},
)
async def list_devices(
    account_id: UUID = Depends(get_account_id),
    service: DeviceService = Depends(provide(DeviceService)),
) -> list[DeviceResponse]:
    """Return every device in the caller's account.

    Accepts either a web (account) session or a device session — a device list is
    account-scoped and non-secret, and the web needs it to show your devices and
    drive device approval. `get_account_id` resolves either token to its account.
    """
    devices = await service.list_for_account(account_id)
    return [DeviceResponse.from_domain(d) for d in devices]


@router.post(
    "/heartbeat",
    response_model=DeviceResponse,
    summary="Keep this device alive",
    responses={401: {"description": "Missing, invalid, expired, or revoked bearer token."}},
)
async def heartbeat(
    body: HeartbeatRequest,
    principal: DevicePrincipal = Depends(get_principal),
    service: DeviceService = Depends(provide(DeviceService)),
) -> DeviceResponse:
    """Extend this device's expiry while it's in use.

    A self-declaring device (a browser) calls this periodically so it survives as
    long as it stays active; stop calling and it expires and is reaped. Only the
    caller's own session is affected — an already-expired device can't get here,
    it fails authentication first.
    """
    device = await service.heartbeat(
        principal.device_id, account_id=principal.account_id, ttl_seconds=body.ttl_seconds
    )
    return DeviceResponse.from_domain(device)


@router.get(
    "/{device_id}",
    response_model=DeviceResponse,
    summary="Fetch a device by id",
    responses={
        401: {"description": "Missing, invalid, or expired bearer token."},
        404: {"description": "No such device in the caller's account."},
    },
)
async def fetch_device(
    device_id: UUID,
    principal: DevicePrincipal = Depends(get_principal),
    service: DeviceService = Depends(provide(DeviceService)),
) -> DeviceResponse:
    """Return a single device by its id, within the caller's account.

    A device belonging to another account is reported as 404, not disclosed.
    """
    device = await service.fetch(device_id, account_id=principal.account_id)
    return DeviceResponse.from_domain(device)
