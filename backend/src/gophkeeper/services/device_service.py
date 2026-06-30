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
        device_name: str,
        public_key: str,
    ) -> Device:
        """Bootstrap a new account from its first device.

        A device is identified by its public key, so the id is minted here rather
        than trusted from the client. Each registration creates a fresh account
        owning this one active device; linking further devices into an existing
        account is the enrollment handshake (a later milestone).
        """
        async with self._uow as uow:
            existing = await uow.devices.find_by_public_key(public_key)
            if existing is not None:
                raise DeviceAlreadyExists(existing.id)

            account = Account(id=uuid4())
            await uow.accounts.add(account)

            device = Device(
                id=uuid4(),
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
