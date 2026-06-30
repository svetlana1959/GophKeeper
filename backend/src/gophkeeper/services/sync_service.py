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

from dataclasses import dataclass
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


@dataclass
class PushResult:
    id: UUID
    status: str  # "applied" | "conflict"
    version: int
    seq: int


class SyncService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def push(self, *, account_id: str, items: list[PushItem]) -> list[PushResult]:
        results: list[PushResult] = []
        async with self._uow as uow:
            for item in items:
                try:
                    secret = await uow.secrets.get(item.id)
                except SecretNotFound:
                    secret = None

                if secret is None:
                    secret = Secret(
                        id=item.id,
                        account_id=account_id,
                        ciphertext=item.ciphertext,
                        deleted=item.deleted,
                    )
                    await uow.secrets.add(secret)
                    results.append(self._applied(secret))
                    continue

                if secret.account_id != account_id:
                    # Not this account's secret — report a conflict without
                    # leaking the real state.
                    results.append(PushResult(item.id, "conflict", 0, 0))
                    continue

                try:
                    if item.deleted:
                        secret.delete()
                    else:
                        secret.update(item.ciphertext, base_version=item.base_version)
                except VersionConflict:
                    results.append(PushResult(item.id, "conflict", secret.version, secret.seq))
                    continue

                await uow.secrets.save(secret)
                results.append(self._applied(secret))

            await uow.commit()
        return results

    async def changes(
        self, *, account_id: str, since: int, limit: int = _DEFAULT_LIMIT
    ) -> tuple[list[Secret], int]:
        async with self._uow as uow:
            secrets = await uow.secrets.list_changed_since(account_id, since, limit=limit)
        cursor = max((s.seq for s in secrets), default=since)
        return secrets, cursor

    @staticmethod
    def _applied(secret: Secret) -> PushResult:
        return PushResult(secret.id, "applied", secret.version, secret.seq)
