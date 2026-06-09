"""Wire-contract DTOs.

These Pydantic models are the request/response shapes the CLI talks to — the
published language of the HTTP API, kept separate from the ``Secret`` domain
object. Ciphertext travels base64-encoded so it survives JSON.
"""

import base64

from pydantic import BaseModel, field_validator

from gophkeeper.domain.secret import Secret


class StoreSecretRequest(BaseModel):
    id: str
    account_id: str
    ciphertext_b64: str

    @field_validator("ciphertext_b64")
    @classmethod
    def _valid_base64(cls, value: str) -> str:
        try:
            base64.b64decode(value, validate=True)
        except (ValueError, base64.binascii.Error) as exc:  # type: ignore[attr-defined]
            raise ValueError("ciphertext_b64 must be valid base64") from exc
        return value

    @property
    def ciphertext(self) -> bytes:
        return base64.b64decode(self.ciphertext_b64)


class UpdateSecretRequest(BaseModel):
    ciphertext_b64: str
    base_version: int

    @property
    def ciphertext(self) -> bytes:
        return base64.b64decode(self.ciphertext_b64)


class SecretResponse(BaseModel):
    id: str
    account_id: str
    version: int
    deleted: bool
    updated_at: str
    ciphertext_b64: str

    @classmethod
    def from_domain(cls, secret: Secret) -> "SecretResponse":
        return cls(
            id=secret.id,
            account_id=secret.account_id,
            version=secret.version,
            deleted=secret.deleted,
            updated_at=secret.updated_at.isoformat(),
            ciphertext_b64=base64.b64encode(secret.ciphertext).decode("ascii"),
        )
