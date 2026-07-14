"""Devices DTOs"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from gophkeeper.domain.device import Device


class DeviceResponse(BaseModel):
    id: UUID
    account_id: UUID
    device_name: str
    public_key: str
    sign_public_key: str = Field(
        description="Ed25519 signing public key (base64); verifies the device's trust certs."
    )
    status: str = Field(description="Trust lifecycle: pending | active | revoked.")
    last_seen_at: datetime | None = Field(description="Last authenticated call, if any.")
    updated_at: datetime

    @classmethod
    def from_domain(cls, device: Device) -> "DeviceResponse":
        return cls(
            id=device.id,
            account_id=device.account_id,
            device_name=device.device_name,
            public_key=device.public_key,
            sign_public_key=device.sign_public_key,
            status=device.status,
            last_seen_at=device.last_seen_at,
            updated_at=device.updated_at,
        )
