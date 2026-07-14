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

from gophkeeper.domain.errors import InvalidInvite


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class Invite:
    id: UUID
    account_id: UUID
    code_hash: str
    expires_at: datetime
    roster_json: str = "[]"  # inviter's trusted devices, MAC'd under the code
    join_mac: str = ""  # set on join: binds the joiner's keys to the code
    joined_device_id: UUID | None = None  # the device that redeemed the code
    consumed_at: datetime | None = None
    created_at: datetime = field(default_factory=_now)

    def is_valid(self, *, at: datetime | None = None) -> bool:
        now = at or _now()
        return self.consumed_at is None and self.expires_at > now

    def consume(self, *, at: datetime | None = None) -> None:
        """Mark the invite used. Guarded: a consumed or expired invite cannot be
        consumed again, so the single-use rule lives on the aggregate rather
        than in service call-ordering. The repository enforces the same rule at
        the row level (conditional UPDATE) to close the concurrent-join race."""
        at = at or _now()
        if not self.is_valid(at=at):
            raise InvalidInvite("invalid or expired invite code")
        self.consumed_at = at


class InviteRepository(Protocol):
    async def add(self, invite: Invite) -> None: ...

    async def find_by_code_hash(self, code_hash: str) -> Invite | None: ...

    async def find_by_id(self, invite_id: UUID) -> Invite | None: ...

    async def consume(self, invite: Invite) -> bool:
        """Persist consumption only if the row is still unconsumed, recording the
        join proof (join_mac + joined_device_id). Returns True if this call won
        the race, False if another join consumed it first."""
        ...
