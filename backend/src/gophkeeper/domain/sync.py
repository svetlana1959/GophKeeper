"""Synchronization value objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class SyncOutcome(StrEnum):
    """What happened to one secret during a sync pass."""

    UPDATED = "UPDATED"
    UP_TO_DATE = "UP_TO_DATE"
    NEW = "NEW"
    ACCESS_REVOKED = "ACCESS_REVOKED"


class SyncStatus(StrEnum):
    """The overall result of one sync call."""

    OK = "OK"
    PARTIAL = "PARTIAL"


@dataclass(frozen=True)
class ClientSecretState:
    """One entry of the client's local sync state."""

    id: UUID
    version: int


@dataclass(frozen=True)
class SyncResult:
    """The outcome for a single secret within a sync pass."""

    secret_id: UUID
    outcome: SyncOutcome
    version: int | None = None
    ciphertext: bytes | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class SyncReport:
    """The full result of one sync call."""

    status: SyncStatus
    results: list[SyncResult]

    @property
    def has_failures(self) -> bool:
        return any(r.outcome == SyncOutcome.ACCESS_REVOKED for r in self.results)
