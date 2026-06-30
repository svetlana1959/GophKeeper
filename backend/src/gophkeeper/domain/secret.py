"""Secret aggregate and repository ports."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from gophkeeper.domain.errors import DomainError, VersionConflict


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class Secret:
    id: UUID
    account_id: str
    ciphertext: bytes  # opaque to the server; encrypted on the client
    version: int = 1
    deleted: bool = False
    updated_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        """Validate after dataclass initialization."""
        self._validate()

    def _validate(self) -> None:
        """Validate aggregate invariants."""
        if not self.account_id:
            raise DomainError("secret account_id must not be empty")
        if not self.ciphertext:
            raise DomainError("secret ciphertext must not be empty")
        if self.version < 1:
            raise DomainError(f"secret version must be >= 1, got {self.version}")

    def update(self, ciphertext: bytes, *, base_version: int, at: datetime | None = None) -> None:
        """Replace ciphertext, rejecting a stale write."""
        if base_version != self.version:
            raise VersionConflict(self.id, expected=base_version, actual=self.version)
        self.ciphertext = ciphertext
        self.version += 1
        self.updated_at = at or _now()
        self._validate()

    def delete(self, *, at: datetime | None = None) -> None:
        """Tombstone the secret."""
        if self.deleted:
            return
        self.deleted = True
        self.version += 1
        self.updated_at = at or _now()

    @property
    def is_active(self) -> bool:
        return not self.deleted


class SecretRepository(Protocol):
    """Port for persisting Secret aggregates."""

    async def add(self, secret: Secret) -> None:
        """Insert a new secret."""
        ...

    async def get(self, secret_id: UUID) -> Secret:
        """Return a secret by id, or raise ``SecretNotFound``."""
        ...

    async def list_for_account(
        self, account_id: str, *, include_deleted: bool = False
    ) -> list[Secret]:
        """Return all secrets owned by an account."""
        ...

    async def save(self, secret: Secret) -> None:
        """Persist changes to an existing secret (update)."""
        ...


class SecretAccessRepository(Protocol):
    """Port for device access grants to secrets."""

    async def grant(self, secret_id: UUID, device_id: UUID) -> None:
        """Give a device access to a secret. Idempotent — granting twice is a no-op."""
        ...

    async def revoke(self, secret_id: UUID, device_id: UUID) -> None:
        """Take away a device's access to a secret. Idempotent."""
        ...

    async def has_access(self, secret_id: UUID, device_id: UUID) -> bool:
        """Whether this device currently has a grant for this secret."""
        ...

    async def list_secret_ids_for_device(self, device_id: UUID) -> list[UUID]:
        """All secret ids this device is trusted to access (for sync)."""
        ...

    async def list_device_ids_for_secret(self, secret_id: UUID) -> list[UUID]:
        """All devices currently trusted with this secret."""
        ...
