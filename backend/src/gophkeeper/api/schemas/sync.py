"""Wire-contract DTOs for synchronization."""

import base64
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from gophkeeper.domain.sync import ClientSecretState, SyncReport, SyncResult


class ClientSecretStateRequest(BaseModel):
    id: UUID
    version: int


class SyncRequest(BaseModel):
    client_state: list[ClientSecretStateRequest]

    def to_domain(self) -> list[ClientSecretState]:
        return [ClientSecretState(id=e.id, version=e.version) for e in self.client_state]


class SyncResultResponse(BaseModel):
    secret_id: UUID
    outcome: str
    version: int | None = None
    ciphertext_b64: str | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_domain(cls, result: SyncResult) -> "SyncResultResponse":
        return cls(
            secret_id=result.secret_id,
            outcome=result.outcome.value,
            version=result.version,
            ciphertext_b64=(
                base64.b64encode(result.ciphertext).decode("ascii")
                if result.ciphertext is not None
                else None
            ),
            updated_at=result.updated_at,
        )


class SyncReportResponse(BaseModel):
    status: str
    results: list[SyncResultResponse]

    @classmethod
    def from_domain(cls, report: SyncReport) -> "SyncReportResponse":
        return cls(
            status=report.status.value,
            results=[SyncResultResponse.from_domain(r) for r in report.results],
        )
