"""Trust-log certificates — the append-only record of the device trust graph.

The server stores signed vouch/revoke certs opaquely and never verifies their
signatures; clients do that and recompute the trusted set locally. The only rule
the server enforces is that an issuer's ``issuer_seq`` is contiguous, so a
device's certs form a gap-free, tamper-evident chain. See docs/sync_design.md §11.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID


@dataclass
class TrustCert:
    id: UUID
    account_id: UUID
    issuer_device_id: UUID
    issuer_seq: int
    kind: str
    payload: dict[str, Any]  # the opaque signed cert, as the client published it
    log_seq: int = 0  # global cursor; assigned by the DB on add


class TrustCertRepository(Protocol):
    async def add(self, cert: TrustCert) -> int:
        """Append a cert; return its assigned log_seq."""
        ...

    async def max_issuer_seq(self, issuer_device_id: UUID) -> int | None:
        """The issuer's highest published issuer_seq, or None if it has none."""
        ...

    async def list_since(self, account_id: UUID, since: int, *, limit: int) -> list[TrustCert]:
        """Certs for the account with log_seq > since, in log_seq order."""
        ...
