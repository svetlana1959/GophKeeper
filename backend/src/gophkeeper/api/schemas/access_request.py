"""Wire-contract DTOs for the access-request handshake broker (issue #69)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from gophkeeper.domain.access_request import AccessRequest


class AccessRequestResponse(BaseModel):
    id: UUID
    secret_id: UUID
    device_id: UUID
    status: str
    updated_at: datetime

    @classmethod
    def from_domain(cls, request: AccessRequest) -> "AccessRequestResponse":
        return cls(
            id=request.id,
            secret_id=request.secret_id,
            device_id=request.device_id,
            status=request.status.value,
            updated_at=request.updated_at,
        )
