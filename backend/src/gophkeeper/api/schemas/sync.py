"""Sync wire-contract DTOs.

The account is never in the body — it comes from the authenticated session — so
a device can only sync its own account. Ciphertext travels base64-encoded.
"""

import base64
import binascii
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from gophkeeper.domain.secret import Secret


class PushItemRequest(BaseModel):
    id: UUID = Field(description="Client-generated secret id (stable across devices).")
    ciphertext_b64: str = Field(
        default="", description="Base64 opaque ciphertext; may be empty only for a tombstone."
    )
    base_version: int = Field(
        default=0, description="Server version the client edited (0 to create); guards concurrency."
    )
    deleted: bool = Field(default=False, description="True to tombstone the secret.")
    recipients: list[str] = Field(
        default=[], description="age public keys the secret is sealed to (who may pull it)."
    )

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


class PushResultStatus(StrEnum):
    APPLIED = "applied"
    CONFLICT = "conflict"


class PushResultResponse(BaseModel):
    id: UUID
    status: PushResultStatus = Field(description="Per-item push outcome.")
    version: int = Field(description="Resulting (or current, on conflict) server version.")
    seq: int = Field(description="Resulting sync sequence (0 on conflict).")


class PushResponse(BaseModel):
    results: list[PushResultResponse]


class ChangedSecretResponse(BaseModel):
    id: UUID
    version: int
    deleted: bool = Field(description="True for a tombstone (deleted secret).")
    updated_at: datetime
    seq: int = Field(description="Sync sequence; pass the max back as the next cursor.")
    ciphertext_b64: str = Field(description="Base64 opaque ciphertext.")

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
    cursor: int = Field(description="New high-water seq; pass as `since` on the next pull.")
