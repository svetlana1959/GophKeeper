"""Reusable real-API setup helpers for integration tests."""

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


async def register_account(client: AsyncClient, *, label: str) -> AccountSession:
    email = f"{label}-{uuid4()}@example.test"
    response = await client.post(
        "/accounts",
        json={"email": email, "password": _PASSWORD},
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]

    me = await client.get("/accounts/me", headers=bearer(token))
    assert me.status_code == 200, me.text
    return AccountSession(id=UUID(me.json()["id"]), token=token)


async def authenticate_device(
    client: AsyncClient, *, device_id: UUID, account_id: UUID, identity: x25519.Identity
) -> DeviceSession:
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


async def join_device(client: AsyncClient, *, inviter_token: str, name: str) -> DeviceSession:
    identity = x25519.Identity.generate()
    public_key = str(identity.to_public())
    code_hash = hashlib.sha256(uuid4().bytes).hexdigest()

    invite = await client.post(
        "/enroll/invite",
        headers=bearer(inviter_token),
        json={"code_hash": code_hash, "roster": []},
    )
    assert invite.status_code == 200, invite.text

    join = await client.post(
        "/enroll/join",
        json={
            "code_hash": code_hash,
            "device_name": name,
            "public_key": public_key,
            "sign_public_key": f"sign-{name}-{uuid4()}",
            "join_mac": f"mac-{uuid4()}",
        },
    )
    assert join.status_code == 201, join.text
    device = join.json()["device"]

    return await authenticate_device(
        client,
        device_id=UUID(device["id"]),
        account_id=UUID(device["account_id"]),
        identity=identity,
    )
