"""Sync wire-contract DTOs.

The account is never in the body — it comes from the authenticated session — so
a device can only sync its own account. Ciphertext travels base64-encoded.
"""

import base64
import binascii
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator, model_validator

from gophkeeper.domain.secret import Secret


class PushItemRequest(BaseModel):
    id: UUID
    ciphertext_b64: str = ""  # empty allowed only for a pure tombstone
    base_version: int = 0
    deleted: bool = False
    recipients: list[str] = []  # age public keys the secret is sealed to

    @field_validator("ciphertext_b64")
    @classmethod
    def _valid_base64(cls, value: str) -> str:
        if value == "":
            return value
        try:
            base64.b64decode(value, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError("ciphertext_b64 must be valid base64") from exc
        return value

    @model_validator(mode="after")
    def _ciphertext_required_unless_deleted(self) -> "PushItemRequest":
        if not self.deleted and self.ciphertext_b64 == "":
            raise ValueError("ciphertext_b64 is required unless deleted is true")
        return self

    @property
    def ciphertext(self) -> bytes:
        return base64.b64decode(self.ciphertext_b64) if self.ciphertext_b64 else b""


class PushRequest(BaseModel):
    items: list[PushItemRequest]


class PushResultResponse(BaseModel):
    id: UUID
    status: str
    version: int
    seq: int


class PushResponse(BaseModel):
    results: list[PushResultResponse]


class ChangedSecretResponse(BaseModel):
    id: UUID
    version: int
    deleted: bool
    updated_at: datetime
    seq: int
    ciphertext_b64: str

    @classmethod
    def from_domain(cls, secret: Secret) -> "ChangedSecretResponse":
        return cls(
            id=secret.id,
            version=secret.version,
            deleted=secret.deleted,
            updated_at=secret.updated_at,
            seq=secret.seq,
            ciphertext_b64=base64.b64encode(secret.ciphertext).decode("ascii"),
        )


class ChangesResponse(BaseModel):
    secrets: list[ChangedSecretResponse]
    cursor: int
