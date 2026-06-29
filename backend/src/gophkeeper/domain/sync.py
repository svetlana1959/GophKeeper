"""Synchronization value objects (issue #68).

Synchronization is not a new aggregate with its own table — it is a read-side
comparison over data that already exists (``Secret.version``, the
``secret_access`` grants from issue #69). These are plain value objects
describing *the outcome* of that comparison, returned by
``services.sync_service.SyncService.sync()``.

Per acceptance criteria:
  - "the user receives the sync status"      -> SyncResult.status (per item)
                                                  and SyncReport.status (overall)
  - "the user is notified about the error"   -> SyncOutcome.ACCESS_REVOKED is
                                                  an explicit per-item outcome,
                                                  not a silent omission
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class SyncOutcome(StrEnum):
    """What happened to one secret during a sync pass.

    UPDATED: the server has a newer version than the client reported; the
        client should apply the returned ciphertext/version locally.
    UP_TO_DATE: client and server already agree on the version; nothing to do.
    NEW: the server knows a secret the client didn't mention at all — e.g.
        another device created it, or this device just gained access via the
        issue #69 handshake. Treated as a normal sync outcome, not an error:
        discovering new secrets is the whole point of sync.
    ACCESS_REVOKED: the client asked about a secret_id it no longer (or
        never did) have access to. This is the explicit failure case
        acceptance criterion #4 asks for — the caller is told exactly which
        item failed and why, rather than the item silently vanishing from
        the response.
    """

    UPDATED = "UPDATED"
    UP_TO_DATE = "UP_TO_DATE"
    NEW = "NEW"
    ACCESS_REVOKED = "ACCESS_REVOKED"


class SyncStatus(StrEnum):
    """The overall result of one sync call, criterion #3's "sync status".

    OK: every requested item resolved cleanly (UPDATED/UP_TO_DATE/NEW).
    PARTIAL: at least one item came back ACCESS_REVOKED. The sync as a whole
        still ran and the caller still gets every result it's entitled to —
        PARTIAL means "some individual items failed", not "the operation
        crashed". A total failure (e.g. the calling device itself being
        untrusted) is a 403 at the HTTP layer instead, never a SyncReport.
    """

    OK = "OK"
    PARTIAL = "PARTIAL"


@dataclass(frozen=True)
class ClientSecretState:
    """One entry of what the client believes it has locally, sent in a sync
    request. ``version`` is the client's last-known version for this secret
    id — analogous to ``base_version`` in ``Secret.update()``, but read-only
    here: sync never writes, it only compares and reports.
    """

    id: UUID
    version: int


@dataclass(frozen=True)
class SyncResult:
    """The outcome for a single secret within a sync pass.

    ``ciphertext``/``version``/``updated_at`` are populated for UPDATED and
    NEW (the client needs the payload to catch up) and left ``None`` for
    UP_TO_DATE (nothing to send, the client already has it) and
    ACCESS_REVOKED (the server won't disclose ciphertext for a secret the
    caller isn't trusted with — that would defeat the access check entirely).
    """

    secret_id: UUID
    outcome: SyncOutcome
    version: int | None = None
    ciphertext: bytes | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class SyncReport:
    """The full result of one ``SyncService.sync()`` call — the "sync status"
    acceptance criterion #3 asks the user to receive, and the carrier for
    criterion #4's per-item error notification.
    """

    status: SyncStatus
    results: list[SyncResult]

    @property
    def has_failures(self) -> bool:
        return any(r.outcome == SyncOutcome.ACCESS_REVOKED for r in self.results)
