"""Application service for devices."""

from uuid import UUID, uuid4

from gophkeeper.domain.account import Account
from gophkeeper.domain.device import ACTIVE, Device
from gophkeeper.domain.errors import DeviceAlreadyExists
from gophkeeper.domain.unit_of_work import UnitOfWork


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
        """Bootstrap a new account from its first device.

        Each registration creates a fresh account owning this one active device.
        Linking further devices into an existing account is the enrollment
        handshake (a later milestone).
        """
        async with self._uow as uow:
            if await uow.devices.exists(device_id):
                raise DeviceAlreadyExists(device_id)

            account = Account(id=uuid4())
            await uow.accounts.add(account)

            device = Device(
                id=device_id,
                account_id=account.id,
                device_name=device_name,
                public_key=public_key,
                status=ACTIVE,
            )
            await uow.devices.add(device)
            await uow.commit()
            return device

    async def fetch(self, device_id: UUID) -> Device:
        async with self._uow as uow:
            return await uow.devices.get(device_id)
