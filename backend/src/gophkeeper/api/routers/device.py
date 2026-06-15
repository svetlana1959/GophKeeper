"""Devices endpoints"""

from fastapi import APIRouter, Depends, status

from gophkeeper.api.deps import provide
from gophkeeper.api.schemas.device import (
    RegisterDeviceRequest,
    DeviceResponse,
)
from gophkeeper.services.device_service import DeviceService

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def register_device(
    body: RegisterDeviceRequest,
    service: DeviceService = Depends(provide(DeviceService)),
) -> DeviceResponse:
    device = await service.register(
        device_id=body.id,
        device_name=body.device_name,
        public_key=body.public_key,
    )
    return DeviceResponse.from_domain(device)


@router.get("/{device_id}", response_model=DeviceResponse)
async def fetch_device(
    device_id: str,
    service: DeviceService = Depends(provide(DeviceService)),
) -> DeviceResponse:
    device = await service.fetch(device_id)
    return DeviceResponse.from_domain(device)
