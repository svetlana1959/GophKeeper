"""The Secret aggregate and its repository port.

EXAMPLE aggregate. This is the reference for the whole domain layer: a model
that carries its own behavior and invariants, plus the repository *interface*
(port) it needs — defined right next to the type it serves, never in a shared
``repositories.py`` grab-bag. Device and the device-authorization mailbox will
follow exactly this shape.

The domain imports only the standard library and its own errors — never
SQLAlchemy, FastAPI, or asyncpg. Storage and transport are details that depend
on the domain, not the reverse.

GophKeeper is a *blind* store: ``ciphertext`` is opaque bytes encrypted on the
client. The server never holds a key and cannot read it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from gophkeeper.domain.errors import DomainError, VersionConflict


def _now() -> datetime:
    return datetime.now(UTC)


"""
We could use Pydantic, and it won't be wrong, though we have rule about domain
importing only base libs.
Also not using Pydantic make it impossible to use domain model as DTO in the API
"""


@dataclass
class Secret:
    id: str
    account_id: str
    ciphertext: bytes  # opaque to the server; encrypted on the client
    version: int = 1
    deleted: bool = False
    updated_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        """Validate right after the dataclass __init__, so no Secret can exist in
        an invalid state regardless of who built it (a use case, a repository
        loading a row, a test).
        """
        self._validate()

    def _validate(self) -> None:
        """The aggregate's invariants. Raises DomainError — the domain's own
        vocabulary — not a framework's ValidationError. Called on construction
        and after any mutation, so the rules hold for the object's whole life.
        """
        if not self.id:
            # NOTE: Probably should create separate Error for this,
            # but can't be bothered with it rn
            raise DomainError("secret id must not be empty")
        if not self.account_id:
            raise DomainError("secret account_id must not be empty")
        if not self.ciphertext:
            raise DomainError("secret ciphertext must not be empty")
        if self.version < 1:
            raise DomainError(f"secret version must be >= 1, got {self.version}")

    def update(
        self, ciphertext: bytes, *, base_version: int, at: datetime | None = None
    ) -> None:
        """Replace the ciphertext, rejecting a stale write.

        ``base_version`` is the version the client believed it was editing. If it
        no longer matches, another device got there first and we raise rather
        than silently clobber their write.
        """
        if base_version != self.version:
            raise VersionConflict(self.id, expected=base_version, actual=self.version)
        self.ciphertext = ciphertext
        self.version += 1
        self.updated_at = at or _now()
        self._validate()

    def delete(self, *, at: datetime | None = None) -> None:
        """Tombstone the secret so the deletion syncs to other devices.

        Idempotent: deleting an already-deleted secret is a no-op.
        """
        if self.deleted:
            return
        self.deleted = True
        self.version += 1
        self.updated_at = at or _now()

    @property
    def is_active(self) -> bool:
        return not self.deleted


class SecretRepository(Protocol):
    """Port for persisting Secret aggregates (a ``typing.Protocol``).

    Lives in the domain next to the aggregate it serves. Any object with these
    methods satisfies it: the SQLAlchemy adapter in
    ``gophkeeper.infrastructure.repositories`` implements it, and a test can pass
    a lightweight fake without subclassing anything. The type checker verifies
    conformance wherever an implementation is used as a ``SecretRepository``.
    """

    async def add(self, secret: Secret) -> None:
        """Insert a new secret."""
        ...

    async def get(self, secret_id: str) -> Secret:
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
