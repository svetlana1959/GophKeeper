"""Application service for multi-device synchronization."""

from uuid import UUID

from gophkeeper.domain.errors import AccessDenied
from gophkeeper.domain.sync import (
    ClientSecretState,
    SyncOutcome,
    SyncReport,
    SyncResult,
    SyncStatus,
)
from gophkeeper.domain.unit_of_work import UnitOfWork


class SyncService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def sync(self, *, device_id: UUID, client_state: list[ClientSecretState]) -> SyncReport:
        """Compare the client's reported state against the server's."""
        async with self._uow as uow:
            device = await uow.devices.get(device_id)
            if not device.is_active:
                raise AccessDenied(device_id)

            accessible_ids = set(await uow.access.list_secret_ids_for_device(device_id))
            client_by_id = {entry.id: entry for entry in client_state}

            results: list[SyncResult] = []

            for secret_id, entry in client_by_id.items():
                if secret_id not in accessible_ids:
                    results.append(
                        SyncResult(secret_id=secret_id, outcome=SyncOutcome.ACCESS_REVOKED)
                    )
                    continue

                secret = await uow.secrets.get(secret_id)
                if secret.version > entry.version:
                    results.append(
                        SyncResult(
                            secret_id=secret_id,
                            outcome=SyncOutcome.UPDATED,
                            version=secret.version,
                            ciphertext=secret.ciphertext,
                            updated_at=secret.updated_at,
                        )
                    )
                else:
                    results.append(SyncResult(secret_id=secret_id, outcome=SyncOutcome.UP_TO_DATE))

            for secret_id in accessible_ids - client_by_id.keys():
                secret = await uow.secrets.get(secret_id)
                results.append(
                    SyncResult(
                        secret_id=secret_id,
                        outcome=SyncOutcome.NEW,
                        version=secret.version,
                        ciphertext=secret.ciphertext,
                        updated_at=secret.updated_at,
                    )
                )

            status = (
                SyncStatus.PARTIAL
                if any(r.outcome == SyncOutcome.ACCESS_REVOKED for r in results)
                else SyncStatus.OK
            )

            return SyncReport(status=status, results=results)
