"""Auth DTOs.

Binary fields (the age-encrypted challenge, the nonce answer) cross the wire as
base64 strings.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class ChallengeRequest(BaseModel):
    public_key: str = Field(description="The device's age public key (age1…).")


class ChallengeResponse(BaseModel):
    challenge: str = Field(
        description="Base64 age ciphertext; decrypt with the device private key."
    )
    challenge_token: str = Field(
        description="Opaque token binding this challenge; return it to verify."
    )


class VerifyRequest(BaseModel):
    challenge_token: str = Field(description="The token from /auth/challenge.")
    nonce: str = Field(description="Base64 of the decrypted challenge nonce.")


class SessionResponse(BaseModel):
    access_token: str = Field(description="Bearer token for Authorization headers.")
    token_type: str = "bearer"
    expires_in: int = Field(description="Token lifetime in seconds.")


class WhoAmIResponse(BaseModel):
    device_id: UUID
    account_id: UUID
