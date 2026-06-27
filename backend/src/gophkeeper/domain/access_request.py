"""The AccessRequest aggregate and its repository port.

Multi-device access (issue #69), revised per review: GophKeeper is
Zero-Knowledge, so the server cannot decide that a new device may read a
secret — only the device that already holds the decryption key can, by
re-encrypting the secret's payload for the new device locally and pushing the
result through the existing ``PUT /secrets/{id}``. The server's role here is
purely as an asynchronous broker: it relays *that a device is asking* and
*its public key*, and nothing else. It never inspects, re-encrypts, or
approves anything on its own.

``AccessRequest`` is that relayed message. Its lifecycle is exactly three
states — pending, approved, rejected — and approval/rejection are the only
mutations, mirroring ``Secret.delete()``'s tombstone pattern: a terminal state
is reached once and stays reached.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from gophkeeper.domain.errors import AccessRequestNotPending, DomainError


def _now() -> datetime:
    return datetime.now(UTC)


class AccessRequestStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass
class AccessRequest:
    id: UUID
    secret_id: UUID
    device_id: UUID
    status: AccessRequestStatus = AccessRequestStatus.PENDING
    updated_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if self.secret_id is None:
            raise DomainError("access request secret_id must not be empty")
        if self.device_id is None:
            raise DomainError("access request device_id must not be empty")

    def approve(self, *, at: datetime | None = None) -> None:
        """Mark this request approved.

        Only valid from PENDING — the caller (the service layer) is
        responsible for having just pushed the re-encrypted secret via
        ``PUT /secrets/{id}`` first; this method only records that the
        handshake completed, it does not touch the secret itself.
        """
        if self.status != AccessRequestStatus.PENDING:
            raise AccessRequestNotPending(self.id, current_status=self.status)
        self.status = AccessRequestStatus.APPROVED
        self.updated_at = at or _now()

    def reject(self, *, at: datetime | None = None) -> None:
        """Mark this request rejected. Only valid from PENDING."""
        if self.status != AccessRequestStatus.PENDING:
            raise AccessRequestNotPending(self.id, current_status=self.status)
        self.status = AccessRequestStatus.REJECTED
        self.updated_at = at or _now()

    @property
    def is_pending(self) -> bool:
        return self.status == AccessRequestStatus.PENDING


class AccessRequestRepository(Protocol):
    """Port for persisting AccessRequest aggregates.

    Lives in the domain next to the aggregate it serves, same shape as every
    other repository port in this codebase.
    """

    async def add(self, request: AccessRequest) -> None:
        """Insert a new request. Raises ``AccessRequestAlreadyPending`` if the
        same (secret_id, device_id) pair already has a PENDING row — mirrors
        the partial unique index in the migration, checked here too so the
        domain raises its own vocabulary error instead of surfacing a raw
        constraint violation.
        """
        ...

    async def get(self, request_id: UUID) -> AccessRequest:
        """Return a request by id, or raise ``AccessRequestNotFound``."""
        ...

    async def list_pending_for_secret(self, secret_id: UUID) -> list[AccessRequest]:
        """All PENDING requests for a secret — what its owner needs to act on."""
        ...

    async def save(self, request: AccessRequest) -> None:
        """Persist a status change (approve/reject)."""
        ...
