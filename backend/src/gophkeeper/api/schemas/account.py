"""Web account DTOs (registration, login, session, current account)."""

from uuid import UUID

from pydantic import BaseModel, Field


class RegisterAccountRequest(BaseModel):
    email: str = Field(description="Login email; the account's password identifier.")
    password: str = Field(min_length=8, description="Account password (min 8 chars).")
    recovery_pubkey: str | None = Field(
        default=None,
        description="Recovery age public key, minted in the browser. The private "
        "half is shown to the user once and never sent.",
    )


class LoginRequest(BaseModel):
    email: str = Field(description="Login email.")
    password: str = Field(description="Account password.")


class AccountSessionResponse(BaseModel):
    access_token: str = Field(description="Bearer token for the account (web) session.")
    token_type: str = "bearer"
    expires_in: int = Field(description="Token lifetime in seconds.")


class SetRecoveryKeyRequest(BaseModel):
    recovery_pubkey: str = Field(
        min_length=1,
        description="Recovery age public key, minted in the browser. The private "
        "half is shown to the user once and never sent. Write-once per account.",
    )


class AccountResponse(BaseModel):
    id: UUID
    recovery_pubkey: str | None = Field(
        description="The account's recovery age public key, or null if none is set."
    )
