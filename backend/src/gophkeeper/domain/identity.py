"""The AccountIdentity aggregate and its repository port.

An identity is one way a human proves they own an account on the web. It is kept
deliberately provider-agnostic: ``provider`` names the method, ``identifier`` is
the login handle within that method, and ``secret`` is whatever that method
verifies against — an argon2 password hash for ``password``, and ``None`` for
providers whose proof lives elsewhere (OAuth subjects, etc.). New auth methods
are new ``provider`` values, not new columns or tables.

The domain owns no crypto: hashing/verifying a password is an adapter concern
(``security.passwords``). This aggregate only carries the modeled data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from gophkeeper.domain.errors import DomainError

PASSWORD = "password"  # the only provider today; e.g. "google" joins it later


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class AccountIdentity:
    id: UUID
    account_id: UUID
    provider: str
    identifier: str
    secret: str | None = None
    created_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not self.provider:
            raise DomainError("identity provider must not be empty")
        if not self.identifier:
            raise DomainError("identity identifier must not be empty")


class IdentityRepository(Protocol):
    async def add(self, identity: AccountIdentity) -> None: ...

    async def find(self, provider: str, identifier: str) -> AccountIdentity | None:
        """Return the identity for a (provider, identifier) pair, or None."""
        ...
