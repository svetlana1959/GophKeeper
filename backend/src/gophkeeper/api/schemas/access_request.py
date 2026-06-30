"""Wire-contract DTOs for the access-request handshake broker (issue #69)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from gophkeeper.domain.access_request import AccessRequest, PendingAccessRequest


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


class PendingAccessRequestResponse(AccessRequestResponse):
    """The secret owner's queue view: a pending request plus the requester's
    public key, so the owner can re-encrypt without a second lookup.
    """

    public_key: str

    @classmethod
    def from_pending(cls, pending: PendingAccessRequest) -> "PendingAccessRequestResponse":
        request = pending.request
        return cls(
            id=request.id,
            secret_id=request.secret_id,
            device_id=request.device_id,
            status=request.status.value,
            updated_at=request.updated_at,
            public_key=pending.requester_public_key,
        )
