"""Application service for secrets — the use-case layer.

EXAMPLE service. It orchestrates the domain and the Unit of Work: open the
transaction, drive the aggregate, commit. It holds no business rules itself
(those live on ``Secret``) and knows nothing about HTTP. It depends on the UoW
*port*, so it is trivially testable with a fake.

Multi-device access (issue #69): there is no account/auth layer yet, so trust
is modeled directly between devices and secrets via ``uow.access``. A device
must be both *active* (not deactivated/revoked) and *granted* access to a
secret before it can read or write it. The device that originally stores a
secret is granted access automatically.

REVISION per review: this used to also expose ``share()``/``revoke()``,
letting any device with access grant another device access directly with no
re-encryption step. That is wrong for a Zero-Knowledge system — see
``services/access_request_service.py`` for the replacement, an asynchronous
handshake broker where the server only relays requests and public keys, and a
grant is created only after the owning device has re-encrypted the secret
locally and pushed it through ``update()`` below (unchanged). ``update()``
itself needed no changes for this: it was already the endpoint the owner
re-pushes the re-encrypted payload through.
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
        """Replace a secret's ciphertext.

        This is also the endpoint a secret's owner re-uses to push a
        re-encrypted payload after approving another device's access
        request (issue #69) — no separate "share" write path exists.
        """
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
