"""Builders for driving the real API in integration tests.

Each function performs one real request (or a short, named sequence of them) and
returns a small value object. They compose: ``join_device`` is ``create_invite``
+ ``join_with_code`` + ``authenticate_device``. A test states only what it cares
about and lets the builders supply working defaults for the rest, so the test
body reads as behaviour rather than request plumbing.
"""

import base64
import hashlib
from dataclasses import dataclass
from uuid import UUID, uuid4

from httpx import AsyncClient
from pyrage import decrypt, x25519

_PASSWORD = "integration-password"


@dataclass(frozen=True)
class AccountSession:
    id: UUID
    token: str


@dataclass(frozen=True)
class DeviceSession:
    id: UUID
    account_id: UUID
    identity: x25519.Identity
    public_key: str
    token: str


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def register_account(client: AsyncClient, *, label: str = "account") -> AccountSession:
    """Register a fresh account (unique email) and return its web session."""
    email = f"{label}-{uuid4()}@example.test"
    response = await client.post("/accounts", json={"email": email, "password": _PASSWORD})
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]

    me = await client.get("/accounts/me", headers=bearer(token))
    assert me.status_code == 200, me.text
    return AccountSession(id=UUID(me.json()["id"]), token=token)


async def set_recovery_key(
    client: AsyncClient, *, token: str, pubkey: str = "age1recoverypublickey"
):
    """Set an account's recovery key. Returns the raw response so callers can
    assert on both the happy path and the write-once 409."""
    return await client.put(
        "/accounts/me/recovery", headers=bearer(token), json={"recovery_pubkey": pubkey}
    )


async def create_invite(client: AsyncClient, *, inviter_token: str) -> str:
    """Register a pairing invite and return the code hash a device joins with."""
    code_hash = hashlib.sha256(uuid4().bytes).hexdigest()
    invite = await client.post(
        "/enroll/invite", headers=bearer(inviter_token), json={"code_hash": code_hash, "roster": []}
    )
    assert invite.status_code == 200, invite.text
    return code_hash


async def join_with_code(
    client: AsyncClient,
    *,
    code_hash: str,
    name: str,
    public_key: str,
    sign_public_key: str | None = None,
    join_mac: str | None = None,
):
    """Redeem an invite code for a device. Returns the raw response so callers can
    assert on rejections (unknown code, duplicate key) as well as success."""
    return await client.post(
        "/enroll/join",
        json={
            "code_hash": code_hash,
            "device_name": name,
            "public_key": public_key,
            "sign_public_key": sign_public_key or f"sign-{name}-{uuid4()}",
            "join_mac": join_mac or f"mac-{uuid4()}",
        },
    )


async def authenticate_device(
    client: AsyncClient, *, device_id: UUID, account_id: UUID, identity: x25519.Identity
) -> DeviceSession:
    """Run the age challenge/response and return a device session token."""
    public_key = str(identity.to_public())
    challenge = await client.post("/auth/challenge", json={"public_key": public_key})
    assert challenge.status_code == 200, challenge.text
    payload = challenge.json()
    nonce = decrypt(base64.b64decode(payload["challenge"]), [identity])

    verify = await client.post(
        "/auth/verify",
        json={
            "challenge_token": payload["challenge_token"],
            "nonce": base64.b64encode(nonce).decode("ascii"),
        },
    )
    assert verify.status_code == 200, verify.text
    return DeviceSession(
        id=device_id,
        account_id=account_id,
        identity=identity,
        public_key=public_key,
        token=verify.json()["access_token"],
    )


async def join_device(
    client: AsyncClient,
    *,
    inviter_token: str,
    name: str,
    identity: x25519.Identity | None = None,
) -> DeviceSession:
    """The whole onboarding path: mint an invite, join it, and authenticate.

    Pass ``identity`` to control the device's keypair (e.g. to reuse a public key
    and trigger the duplicate-device conflict); omit it for a fresh one.
    """
    identity = identity or x25519.Identity.generate()
    code_hash = await create_invite(client, inviter_token=inviter_token)
    join = await join_with_code(
        client, code_hash=code_hash, name=name, public_key=str(identity.to_public())
    )
    assert join.status_code == 201, join.text
    device = join.json()["device"]
    return await authenticate_device(
        client,
        device_id=UUID(device["id"]),
        account_id=UUID(device["account_id"]),
        identity=identity,
    )
