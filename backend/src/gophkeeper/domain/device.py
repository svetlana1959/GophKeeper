"""The Device part

Basically the same features as Secret class, but remade for device needs"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from gophkeeper.domain.errors import DomainError


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class Device:
    id: str
    device_name: str
    public_key: str
    is_active: bool
    updated_at: datetime = field(default_factory=_now)

    def __post_init__(self):
        self._validate()

    def _validate(self):
        if not self.device_name:
            raise DomainError("device_name must not be empty")
        if not self.public_key:
            raise DomainError("public_key must not be empty")

    def deactivate(self):
        self.is_active = False
        self.updated_at = _now()

    def activate(self):
        self.is_active = True
        self.updated_at = _now()


class DeviceRepository(Protocol):
    async def add(self, device: Device) -> None:
        ...

    async def get(self, device_id: str) -> Device:
        ...

    async def list_active(self) -> list[Device]:
        ...

    async def save(self, device: Device) -> None:
        ...
