"""Auth DTOs.

Binary fields (the age-encrypted challenge, the nonce answer) cross the wire as
base64 strings.
"""

from uuid import UUID

from pydantic import BaseModel


class ChallengeRequest(BaseModel):
    public_key: str


class ChallengeResponse(BaseModel):
    challenge: str  # base64 age ciphertext; decrypt with the device private key
    challenge_token: str


class VerifyRequest(BaseModel):
    challenge_token: str
    nonce: str  # base64 of the decrypted challenge


class SessionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class WhoAmIResponse(BaseModel):
    device_id: UUID
    account_id: UUID
