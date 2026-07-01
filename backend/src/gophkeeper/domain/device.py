"""The Device aggregate and its repository port.

A device belongs to an account and is identified to the server by its age public
key — the same key the login challenge is encrypted to. ``status`` tracks its
place in the trust lifecycle:

    pending  -> requested a link, not yet approved by a key-holder
    active   -> a full member; can authenticate and sync
    revoked  -> removed; the server rejects it (terminal)

Only an ``active`` device may authenticate (see ``may_authenticate``). The
transitions are guarded so the lifecycle is a real state machine, not free
field assignment: ``revoked`` is terminal, and ``activate`` only promotes a
``pending`` device.

Note (milestone scope): device linking currently admits the joining device as
``active`` immediately (see ``EnrollmentService.join``). The ``pending`` state
and ``activate`` are the seam for the M4 reshare-gated approval flow, where a
key-holder confirms the link before the device becomes a full member.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from gophkeeper.domain.errors import DomainError

PENDING = "pending"
ACTIVE = "active"
REVOKED = "revoked"
_STATUSES = {PENDING, ACTIVE, REVOKED}


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class Device:
    id: UUID
    account_id: UUID
    device_name: str
    public_key: str
    status: str = ACTIVE
    last_seen_at: datetime | None = None
    updated_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not self.device_name:
            raise DomainError("device_name must not be empty")
        if not self.public_key:
            raise DomainError("public_key must not be empty")
        if self.status not in _STATUSES:
            raise DomainError(f"invalid device status: {self.status!r}")

    @property
    def is_active(self) -> bool:
        return self.status == ACTIVE

    def may_authenticate(self) -> bool:
        """Whether this device is allowed to obtain and use a session.

        The single source of truth for "can this device talk to the server":
        only an active device may. Checked on the challenge/verify path *and*
        on every authenticated request (see ``get_principal``), so revoking a
        device denies it immediately rather than at token expiry.
        """
        return self.status == ACTIVE

    def touch(self, *, at: datetime | None = None) -> None:
        """Record that the device just made an authenticated call."""
        self.last_seen_at = at or _now()
        self.updated_at = self.last_seen_at

    def activate(self) -> None:
        """Promote a pending device to active. Revoked is terminal."""
        if self.status == REVOKED:
            raise DomainError("cannot activate a revoked device")
        self.status = ACTIVE
        self.updated_at = _now()

    def revoke(self) -> None:
        """Remove the device. Terminal and idempotent."""
        self.status = REVOKED
        self.updated_at = _now()


class DeviceRepository(Protocol):
    async def add(self, device: Device) -> None: ...

    async def get(self, device_id: UUID) -> Device: ...

    async def find_by_public_key(self, public_key: str) -> Device | None: ...

    async def exists(self, device_id: UUID) -> bool: ...

    async def list_for_account(self, account_id: UUID) -> list[Device]: ...

    async def save(self, device: Device) -> None: ...
