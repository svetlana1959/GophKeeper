"""Application service for devices"""

from gophkeeper.domain.device import Device
from gophkeeper.domain.unit_of_work import UnitOfWork
from gophkeeper.domain.errors import DeviceAlreadyExists
from uuid import UUID

class DeviceService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def register(
        self,
        *,
        device_id: UUID,
        device_name: str,
        public_key: str,
    ) -> Device:
        async with self._uow as uow:
            if await uow.devices.exists(device_id):
                raise DeviceAlreadyExists(device_id)

            device = Device(
                id=device_id,
                device_name=device_name,
                public_key=public_key,
                is_active=True,
            )

            await uow.devices.add(device)
            await uow.commit()
            return device

    async def fetch(self, device_id: UUID) -> Device:
        async with self._uow as uow:
            return await uow.devices.get(device_id)
