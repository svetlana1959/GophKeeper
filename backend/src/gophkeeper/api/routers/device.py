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


@router.post("", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def register_device(
    body: RegisterDeviceRequest,
    service: DeviceService = Depends(provide(DeviceService)),
) -> DeviceResponse:
    device = await service.register(
        device_name=body.device_name,
        public_key=body.public_key,
    )
    return DeviceResponse.from_domain(device)


@router.get("", response_model=list[DeviceResponse])
async def list_devices(
    principal: DevicePrincipal = Depends(get_principal),
    service: DeviceService = Depends(provide(DeviceService)),
) -> list[DeviceResponse]:
    devices = await service.list_for_account(principal.account_id)
    return [DeviceResponse.from_domain(d) for d in devices]


@router.get("/{device_id}", response_model=DeviceResponse)
async def fetch_device(
    device_id: UUID,
    service: DeviceService = Depends(provide(DeviceService)),
) -> DeviceResponse:
    device = await service.fetch(device_id)
    return DeviceResponse.from_domain(device)
