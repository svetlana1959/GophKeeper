"""AccessRequest aggregate and repository port."""

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
        """Mark this request approved."""
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
    """Port for persisting AccessRequest aggregates."""

    async def add(self, request: AccessRequest) -> None:
        """Insert a new request."""
        ...

    async def get(self, request_id: UUID) -> AccessRequest:
        """Return a request by id, or raise ``AccessRequestNotFound``."""
        ...

    async def list_pending_for_secret(self, secret_id: UUID) -> list[AccessRequest]:
        """Return pending requests for a secret."""
        ...

    async def save(self, request: AccessRequest) -> None:
        """Persist a status change (approve/reject)."""
        ...
