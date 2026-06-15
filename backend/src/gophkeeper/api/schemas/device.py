"""Devices DTOs"""


from pydantic import BaseModel

from gophkeeper.domain.device import Device


class RegisterDeviceRequest(BaseModel):
    id: str
    device_name: str
    public_key: str


class DeviceResponse(BaseModel):
    id: str
    device_name: str
    public_key: str
    is_active: bool
    updated_at: str

    @classmethod
    def from_domain(cls, device: Device):
        return cls(
            id=device.id,
            device_name=device.device_name,
            public_key=device.public_key,
            is_active=device.is_active,
            updated_at=device.updated_at.isoformat(),
        )