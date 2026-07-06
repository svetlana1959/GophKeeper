"""Devices endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from gophkeeper.api.deps import get_principal, provide
from gophkeeper.api.schemas.device import (
    DeviceResponse,
    RegisterDeviceRequest,
)
from gophkeeper.security.principal import DevicePrincipal
from gophkeeper.services.device_service import DeviceService

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post(
    "",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a first device (bootstrap a new account)",
    responses={409: {"description": "This public key is already registered."}},
)
async def register_device(
    body: RegisterDeviceRequest,
    service: DeviceService = Depends(provide(DeviceService)),
) -> DeviceResponse:
    """Create a new account owning this device.

    Used by the first device of an account; the server mints the device id.
    Additional devices join an existing account via `/enroll/join` instead.
    """
    device = await service.register(
        device_name=body.device_name,
        public_key=body.public_key,
    )
    return DeviceResponse.from_domain(device)


@router.get(
    "",
    response_model=list[DeviceResponse],
    summary="List the account's devices",
    responses={401: {"description": "Missing, invalid, or expired bearer token."}},
)
async def list_devices(
    principal: DevicePrincipal = Depends(get_principal),
    service: DeviceService = Depends(provide(DeviceService)),
) -> list[DeviceResponse]:
    """Return every device in the caller's account."""
    devices = await service.list_for_account(principal.account_id)
    return [DeviceResponse.from_domain(d) for d in devices]


@router.post(
    "/self/revoke",
    response_model=DeviceResponse,
    summary="Revoke the current device",
    responses={
        401: {"description": "Missing, invalid, expired, or revoked bearer token."},
        404: {"description": "The authenticated device no longer exists."},
    },
)
async def revoke_self(
    principal: DevicePrincipal = Depends(get_principal),
    service: DeviceService = Depends(provide(DeviceService)),
) -> DeviceResponse:
    """Revoke the caller's own device; another device cannot be targeted."""
    device = await service.revoke_self(
        principal.device_id,
        account_id=principal.account_id,
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
