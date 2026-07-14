"""Enrollment DTOs."""

from datetime import datetime

from pydantic import BaseModel, Field


class CreateInviteResponse(BaseModel):
    code: str = Field(
        description="Plaintext pairing code, returned once; share with the new device."
    )
    expires_at: datetime = Field(description="When the code stops being valid.")


class JoinRequest(BaseModel):
    code: str = Field(description="The pairing code from /enroll/invite.")
    device_name: str = Field(description="Human-readable name for the joining device.")
    public_key: str = Field(description="The joining device's age public key (age1…).")
    sign_public_key: str = Field(
        default="",
        description="The joining device's Ed25519 signing public key (base64), if any.",
    )
