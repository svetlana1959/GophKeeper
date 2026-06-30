"""Devices DTOs"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from gophkeeper.domain.device import Device


class RegisterDeviceRequest(BaseModel):
    device_name: str
    public_key: str


class DeviceResponse(BaseModel):
    id: UUID
    account_id: UUID
    device_name: str
    public_key: str
    status: str
    last_seen_at: datetime | None
    updated_at: datetime

    @classmethod
    def from_domain(cls, device: Device) -> "DeviceResponse":
        return cls(
            id=device.id,
            account_id=device.account_id,
            device_name=device.device_name,
            public_key=device.public_key,
            status=device.status,
            last_seen_at=device.last_seen_at,
            updated_at=device.updated_at,
        )
