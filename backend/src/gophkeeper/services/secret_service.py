"""Application service for secrets — the use-case layer.

EXAMPLE service. It orchestrates the domain and the Unit of Work: open the
transaction, drive the aggregate, commit. It holds no business rules itself
(those live on ``Secret``) and knows nothing about HTTP. It depends on the UoW
*port*, so it is trivially testable with a fake.

Multi-device access (issue #69): there is no account/auth layer yet, so trust
is modeled directly between devices and secrets via ``uow.access``. A device
must be both *active* (not deactivated/revoked) and *granted* access to a
secret before it can read or write it. The device that originally stores a
secret is granted access automatically; any other device needs an explicit
``share()`` call from a device that already has access — mirroring the
device-to-device trust flow described in the product concept docs, just
without the actual key exchange (no crypto happens server-side; the server
only tracks *which* devices may sync *which* ciphertexts).
"""

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
        """Create a new secret and grant the creating device access to it.

        Without this grant the device that just stored the secret would
        immediately fail the access check on its own next fetch — so granting
        happens in the same transaction as the insert, not as an afterthought.
        """
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
        async with self._uow as uow:
            await self._ensure_access(uow, secret_id, device_id)
            secret = await uow.secrets.get(secret_id)
            secret.update(ciphertext, base_version=base_version)  # may raise VersionConflict
            await uow.secrets.save(secret)
            await uow.commit()
            return secret

    async def fetch(self, secret_id: UUID, *, device_id: UUID) -> Secret:
        async with self._uow as uow:
            await self._ensure_access(uow, secret_id, device_id)
            return await uow.secrets.get(secret_id)

    async def list_for_device(self, device_id: UUID) -> list[Secret]:
        """All secrets a device is currently trusted to sync.

        This is the read side of issue #69's sync criteria: a trusted device
        that reconnects calls this to catch up, and gets every secret it has
        an active grant for, regardless of which device last wrote it.
        """
        async with self._uow as uow:
            await self._ensure_device_trusted(uow, device_id)
            secret_ids = await uow.access.list_secret_ids_for_device(device_id)
            return [await uow.secrets.get(secret_id) for secret_id in secret_ids]

    async def share(self, secret_id: UUID, *, from_device_id: UUID, to_device_id: UUID) -> None:
        """Extend trust for a secret to another device.

        ``from_device_id`` must already have access — a device can only
        vouch for a secret it can itself see, it can't grant access to
        something it doesn't hold. ``to_device_id`` must be a known, active
        device (it still needs its own ``DeviceService.register`` call first;
        this only extends *secret* access, it doesn't create devices).
        """
        async with self._uow as uow:
            await self._ensure_access(uow, secret_id, from_device_id)
            await self._ensure_device_trusted(uow, to_device_id)
            await uow.access.grant(secret_id, to_device_id)
            await uow.commit()

    async def revoke(
        self, secret_id: UUID, *, requesting_device_id: UUID, target_device_id: UUID
    ) -> None:
        """Remove a device's access to one secret (e.g. it was lost or compromised)."""

        async with self._uow as uow:
            await self._ensure_access(uow, secret_id, requesting_device_id)
            await uow.access.revoke(secret_id, target_device_id)
            await uow.commit()

    async def _ensure_device_trusted(self, uow: UnitOfWork, device_id: UUID) -> None:
        """A device must exist and be active to do anything at all.

        ``uow.devices.get`` already raises ``DeviceNotFound`` for an unknown
        id; we additionally reject a deactivated device, since "not trusted"
        in issue #69 covers both "never registered" and "revoked".
        """
        device = await uow.devices.get(device_id)
        if not device.is_active:
            raise AccessDenied(device_id)

    async def _ensure_access(self, uow: UnitOfWork, secret_id: UUID, device_id: UUID) -> None:
        await self._ensure_device_trusted(uow, device_id)
        if not await uow.access.has_access(secret_id, device_id):
            raise AccessDenied(device_id, secret_id)
