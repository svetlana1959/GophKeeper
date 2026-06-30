"""The AccessRequest aggregate, its repository port, and the pending read-model.

GophKeeper is Zero-Knowledge: only a device that already holds the decryption
key can let another device in, by re-encrypting the secret locally and pushing
it through ``PUT /secrets/{id}``. The server only relays *that a device is
asking*; it never re-encrypts or grants on its own. ``AccessRequest`` is that
relayed message — a three-state lifecycle (pending -> approved/rejected) where
the terminal states are reached once and stay reached.
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
        """Mark this request approved. Only valid from PENDING.

        Records that the handshake completed; it does not touch the secret —
        the caller is responsible for having pushed the re-encrypted payload
        via ``PUT /secrets/{id}`` first.
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


@dataclass(frozen=True)
class PendingAccessRequest:
    """Read-model: a pending request paired with the requester's current public
    key, looked up live at read time so the approving device has everything it
    needs to re-encrypt in one round-trip. The key is never snapshotted onto the
    request row — a rotated key must not be re-encrypted against.
    """

    request: AccessRequest
    requester_public_key: str


class AccessRequestRepository(Protocol):
    """Port for persisting AccessRequest aggregates."""

    async def add(self, request: AccessRequest) -> None:
        """Insert a new request. Raises ``AccessRequestAlreadyPending`` if the
        same (secret_id, device_id) pair already has a PENDING row.
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
