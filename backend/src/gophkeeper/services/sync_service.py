"""Application service for multi-device synchronization (issue #68).

This is a read-only comparison, not a new write path: it reuses
``uow.secrets`` and ``uow.access`` exactly as ``SecretService`` does (no new
repository, no new table). The novelty is the *shape of the response* — a
per-secret breakdown plus an overall status, which is what acceptance
criteria #3 ("the user receives the sync status") and #4 ("the user is
notified about the error") ask for that a bare ``GET /secrets`` does not
give: that endpoint already exists from issue #69, but it returns "here is
everything you can see" with no notion of what changed, what's new, or what
you lost access to since you last looked.
"""

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
        """Compare the client's reported state against the server's.

        The calling device itself must be known and active — if not, this
        raises ``AccessDenied`` and the HTTP layer returns 403 for the whole
        call (criterion #4 covers per-secret failures; a totally untrusted
        caller is a different, total failure, not a partial one).

        Within an active device's own sync pass, no per-secret access
        problem ever raises: every entry in ``client_state``, plus every
        secret the device has access to but didn't mention, gets its own
        ``SyncResult`` instead. That is what makes the overall response
        PARTIAL rather than an exception — the operation as a whole
        succeeded; specific items within it didn't.
        """
        async with self._uow as uow:
            device = await uow.devices.get(device_id)  # raises DeviceNotFound
            if not device.is_active:
                raise AccessDenied(device_id)

            accessible_ids = set(await uow.access.list_secret_ids_for_device(device_id))
            client_by_id = {entry.id: entry for entry in client_state}

            results: list[SyncResult] = []

            # Everything the client told us about.
            for secret_id, entry in client_by_id.items():
                if secret_id not in accessible_ids:
                    # Covers both "never had access" and "access was
                    # revoked since the client last synced" — the client
                    # cannot tell those apart from its own state, so the
                    # server must say so explicitly rather than just
                    # omitting the id from the response.
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
                    # secret.version == entry.version: up to date.
                    # secret.version < entry.version would mean the client's
                    # reported version is from the future relative to the
                    # server, which Secret's own invariants make impossible
                    # under normal operation (version only increases via
                    # update()/delete()) — treated the same as up-to-date
                    # rather than as a separate error class, since there's
                    # nothing actionable to tell the client either way.
                    results.append(SyncResult(secret_id=secret_id, outcome=SyncOutcome.UP_TO_DATE))

            # Secrets the device can see that it never mentioned — newly
            # granted access (issue #69) or simply never synced before.
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
