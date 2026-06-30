"""Enrollment DTOs."""

from datetime import datetime

from pydantic import BaseModel


class CreateInviteResponse(BaseModel):
    code: str  # plaintext pairing code, shown once
    expires_at: datetime


class JoinRequest(BaseModel):
    code: str
    device_name: str
    public_key: str
