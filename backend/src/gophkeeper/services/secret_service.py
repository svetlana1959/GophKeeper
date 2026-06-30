"""Application service for secrets."""

from uuid import UUID

from gophkeeper.domain.errors import AccessDenied
from gophkeeper.domain.secret import Secret
from gophkeeper.domain.unit_of_work import UnitOfWork


class SecretService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def store(
        self, *, account_id: str, secret_id: UUID, device_id: UUID, ciphertext: bytes
    ) -> Secret:
        """Create a secret and grant the creating device access."""
        async with self._uow as uow:
            await self._ensure_device_trusted(uow, device_id)
            secret = Secret(id=secret_id, account_id=account_id, ciphertext=ciphertext)
            await uow.secrets.add(secret)
            await uow.access.grant(secret_id, device_id)
            await uow.commit()
            return secret

    async def update(
        self, *, secret_id: UUID, device_id: UUID, ciphertext: bytes, base_version: int
    ) -> Secret:
        """Replace a secret's ciphertext."""
        async with self._uow as uow:
            await self._ensure_access(uow, secret_id, device_id)
            secret = await uow.secrets.get(secret_id)
            secret.update(ciphertext, base_version=base_version)
            await uow.secrets.save(secret)
            await uow.commit()
            return secret

    async def fetch(self, secret_id: UUID, *, device_id: UUID) -> Secret:
        async with self._uow as uow:
            await self._ensure_access(uow, secret_id, device_id)
            return await uow.secrets.get(secret_id)

    async def list_for_device(self, device_id: UUID) -> list[Secret]:
        """Return secrets this device may access."""
        async with self._uow as uow:
            await self._ensure_device_trusted(uow, device_id)
            secret_ids = await uow.access.list_secret_ids_for_device(device_id)
            return [await uow.secrets.get(secret_id) for secret_id in secret_ids]

    async def _ensure_device_trusted(self, uow: UnitOfWork, device_id: UUID) -> None:
        """Raise if the device is missing or inactive."""
        device = await uow.devices.get(device_id)
        if not device.is_active:
            raise AccessDenied(device_id)

    async def _ensure_access(self, uow: UnitOfWork, secret_id: UUID, device_id: UUID) -> None:
        await self._ensure_device_trusted(uow, device_id)
        if not await uow.access.has_access(secret_id, device_id):
            raise AccessDenied(device_id, secret_id)
