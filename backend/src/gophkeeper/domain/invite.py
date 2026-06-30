"""The Invite aggregate and its repository port.

An invite is a single-use, expiring pairing code that authorizes a new device to
join an account. Only the code's hash is persisted; the plaintext is shown to the
inviting device once and never stored.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class Invite:
    id: UUID
    account_id: UUID
    code_hash: str
    expires_at: datetime
    consumed_at: datetime | None = None
    created_at: datetime = field(default_factory=_now)

    def is_valid(self, *, at: datetime | None = None) -> bool:
        now = at or _now()
        return self.consumed_at is None and self.expires_at > now

    def consume(self, *, at: datetime | None = None) -> None:
        self.consumed_at = at or _now()


class InviteRepository(Protocol):
    async def add(self, invite: Invite) -> None: ...

    async def find_by_code_hash(self, code_hash: str) -> Invite | None: ...

    async def save(self, invite: Invite) -> None: ...
