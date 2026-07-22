"""Enrollment DTOs.

The inviter generates the code client-side and uploads only its hash plus a
roster of its trusted devices, each MAC'd under the code (see cli/internal/trust).
The server relays the roster to the joiner but cannot forge it.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from gophkeeper.api.schemas.device import DeviceResponse


class RosterEntry(BaseModel):
    device_id: str = Field(description="A trusted device's id.")
    enc_pub: str = Field(description="Its age public key.")
    sign_pub: str = Field(description="Its Ed25519 signing key.")
    mac: str = Field(description="HMAC of the entry under the invite code.")


class CreateInviteRequest(BaseModel):
    code_hash: str = Field(description="Hex SHA-256 of the client-generated code.")
    roster: list[RosterEntry] = Field(
        default_factory=list,
        description="Inviter's trusted devices, MAC'd under the code; empty for the web.",
    )


class CreateInviteResponse(BaseModel):
    invite_id: UUID = Field(description="Handle to poll for the join proof.")
    expires_at: datetime = Field(description="When the code stops being valid.")


class JoinRequest(BaseModel):
    code_hash: str = Field(description="Hex SHA-256 of the pairing code the joiner holds.")
    device_name: str = Field(description="Human-readable name for the joining device.")
    public_key: str = Field(description="The joining device's age public key (age1…).")
    sign_public_key: str = Field(default="", description="Its Ed25519 signing public key (base64).")
    join_mac: str = Field(
        default="", description="HMAC binding the joiner's keys to the code, for the inviter."
    )
    ttl_seconds: int | None = Field(
        default=None,
        gt=0,
        description=(
            "How long this device should live, in seconds from now — set by "
            "self-declaring devices (e.g. a browser) that expire when idle. The "
            "server caps it. Omit for devices that never expire (the CLI)."
        ),
    )


class JoinResponse(BaseModel):
    device: DeviceResponse
    roster: list[RosterEntry] = Field(
        description="The inviter's trusted devices for the joiner to adopt as anchors."
    )


class InviteProofResponse(BaseModel):
    consumed: bool = Field(description="Whether a device has redeemed the invite.")
    join_mac: str = Field(description="The redeeming device's join MAC, once consumed.")
    device: DeviceResponse | None = Field(
        default=None, description="The device that redeemed the invite, if any."
    )
