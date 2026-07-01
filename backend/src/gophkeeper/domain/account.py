"""The Account aggregate and its repository port.

An account is the unit that groups a user's devices and secrets. Devices
authenticate; an account scopes what they can sync. ``recovery_pubkey`` is the
public half of the offline recovery key (set at first sync, used later to gate
emergency revocation and recovery) — it is ``None`` until that key is minted.

Follows the same shape as Secret: a model plus the port it needs, both pure
standard library. Account is a plain data holder today — the account-level
invariants it will own (a minted recovery key, the trusted-device allow-list
that gates emergency revocation) arrive with M4.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class Account:
    id: UUID
    recovery_pubkey: str | None = None
    created_at: datetime = field(default_factory=_now)


class AccountRepository(Protocol):
    async def add(self, account: Account) -> None: ...

    async def get(self, account_id: UUID) -> Account: ...
