"""Application service for synchronization.

push() applies a batch of client changes under optimistic concurrency: each item
is created, updated against its base_version, or tombstoned. A stale item is not
fatal — it comes back as a 'conflict' so the client can pull the winner and
reconcile, while the rest of the batch still applies.

changes() returns the account's delta since a cursor (tombstones included) for
the client to apply, plus the new high-water cursor.

Everything is scoped to one account_id (resolved from the caller's session, not
the request body), so a device can only ever touch its own account's secrets.
"""

from dataclasses import dataclass, field
from uuid import UUID

from gophkeeper.domain.errors import SecretNotFound, VersionConflict
from gophkeeper.domain.secret import Secret
from gophkeeper.domain.unit_of_work import UnitOfWork

_DEFAULT_LIMIT = 500


@dataclass
class PushItem:
    id: UUID
    ciphertext: bytes
    base_version: int = 0
    deleted: bool = False
    recipients: list[str] = field(default_factory=list)  # age public keys


@dataclass
class PushResult:
    id: UUID
    status: str  # "applied" | "conflict"
    version: int
    seq: int


class SyncService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def push(
        self, *, account_id: str, device_id: UUID, items: list[PushItem]
    ) -> list[PushResult]:
        results: list[PushResult] = []
        async with self._uow as uow:
            for item in items:
                try:
                    secret = await uow.secrets.get(item.id)
                except SecretNotFound:
                    secret = None

                if secret is None:
                    if item.deleted:
                        # Deleting a secret the server never had (offline
                        # create-then-delete, or a retry) is a no-op — building a
                        # Secret(ciphertext=b"", deleted=True) would fail the
                        # aggregate's non-empty-ciphertext invariant and 500 the
                        # whole batch.
                        results.append(PushResult(item.id, "applied", 0, 0))
                        continue
                    secret = Secret(
                        id=item.id,
                        account_id=account_id,
                        ciphertext=item.ciphertext,
                    )
                    await uow.secrets.add(secret)
                    # A create always sets the recipient set (pusher included).
                    await self._apply_recipients(uow, account_id, device_id, item)
                    results.append(self._applied(secret))
                    continue

                if secret.account_id != account_id:
                    # Not this account's secret — report a conflict without
                    # leaking the real state.
                    results.append(PushResult(item.id, "conflict", 0, 0))
                    continue

                if item.deleted:
                    secret.delete()
                    await uow.secrets.save(secret)  # tombstone: last write wins
                    results.append(self._applied(secret))
                    continue

                try:
                    secret.update(item.ciphertext, base_version=item.base_version)
                    # expected_version is the pre-update version, so the DB write
                    # is an atomic compare-and-set (see SecretRepository.save).
                    await uow.secrets.save(secret, expected_version=item.base_version)
                except VersionConflict as exc:
                    results.append(PushResult(item.id, "conflict", exc.actual, 0))
                    continue

                # On update, an empty recipient list means "leave sharing as-is".
                # Only an explicit, non-empty set (a reshare) rewrites it — so a
                # plain edit that omits recipients can't silently revoke every
                # other device down to just the pusher.
                if item.recipients:
                    await self._apply_recipients(uow, account_id, device_id, item)
                results.append(self._applied(secret))

            await uow.commit()
        return results

    async def changes(
        self, *, account_id: str, device_id: UUID, since: int, limit: int = _DEFAULT_LIMIT
    ) -> tuple[list[Secret], int]:
        async with self._uow as uow:
            secrets = await uow.secrets.list_changed_since(
                account_id, device_id, since, limit=limit
            )
        cursor = max((s.seq for s in secrets), default=since)
        return secrets, cursor

    async def all_for_account(self, account_id: str) -> list[Secret]:
        """Every live secret in the account, regardless of recipient.

        Unlike ``changes`` (which is scoped to a device's recipient set), this is
        the whole account's ciphertext — needed by a client that decrypts with the
        recovery key, which is a recipient in the ciphertext but not a device. The
        payloads stay opaque; a caller that isn't a recipient still can't read them.
        """
        async with self._uow as uow:
            return await uow.secrets.list_for_account(account_id)

    async def _apply_recipients(
        self, uow: UnitOfWork, account_id: str, device_id: UUID, item: PushItem
    ) -> None:
        """Resolve recipient public keys to account devices and set them. The
        pushing device is always included so the author can always read it."""
        device_ids = {device_id}
        for public_key in item.recipients:
            device = await uow.devices.find_by_public_key(public_key)
            if device is None or str(device.account_id) != account_id:
                continue
            if not device.is_active:
                # Don't reinstate a revoked device into the authorization mirror.
                continue
            device_ids.add(device.id)
        await uow.secrets.set_recipients(item.id, list(device_ids))

    @staticmethod
    def _applied(secret: Secret) -> PushResult:
        return PushResult(secret.id, "applied", secret.version, secret.seq)
