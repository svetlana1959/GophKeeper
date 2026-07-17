"""Device expiry over the API — a self-declaring device sets a TTL at enroll and
extends it with heartbeats. The server never needs to know it's a browser."""

import hashlib
from uuid import UUID, uuid4

import pytest
from pyrage import x25519

from tests.integration.helpers import (
    authenticate_device,
    bearer,
    join_device,
    register_account,
)

pytestmark = pytest.mark.integration


async def _join_with_ttl(api_client, inviter_token, *, name, ttl_seconds):
    """Enroll a device declaring its own TTL, returning its authenticated session
    and the join response body (which carries expires_at)."""
    identity = x25519.Identity.generate()
    code_hash = hashlib.sha256(uuid4().bytes).hexdigest()
    invite = await api_client.post(
        "/enroll/invite", headers=bearer(inviter_token), json={"code_hash": code_hash, "roster": []}
    )
    assert invite.status_code == 200, invite.text
    join = await api_client.post(
        "/enroll/join",
        json={
            "code_hash": code_hash,
            "device_name": name,
            "public_key": str(identity.to_public()),
            "sign_public_key": f"sign-{uuid4()}",
            "join_mac": f"mac-{uuid4()}",
            "ttl_seconds": ttl_seconds,
        },
    )
    assert join.status_code == 201, join.text
    return identity, join.json()["device"]


async def test_enroll_with_ttl_sets_expiry_while_cli_device_never_expires(api_client):
    account = await register_account(api_client, label="ttl")

    _, web_device = await _join_with_ttl(
        api_client, account.token, name="Firefox", ttl_seconds=3600
    )
    assert web_device["expires_at"] is not None

    # A device that declares no TTL (the CLI path) never expires.
    cli = await join_device(api_client, inviter_token=account.token, name="laptop")
    listed = await api_client.get("/devices", headers=bearer(account.token))
    by_id = {d["id"]: d for d in listed.json()}
    assert by_id[str(cli.id)]["expires_at"] is None


async def test_heartbeat_extends_this_devices_expiry(api_client):
    account = await register_account(api_client, label="hb")
    identity, device = await _join_with_ttl(
        api_client, account.token, name="Chrome", ttl_seconds=60
    )
    session = await authenticate_device(
        api_client,
        device_id=UUID(device["id"]),
        account_id=UUID(device["account_id"]),
        identity=identity,
    )
    before = device["expires_at"]

    beat = await api_client.post(
        "/devices/heartbeat", headers=bearer(session.token), json={"ttl_seconds": 86400}
    )
    assert beat.status_code == 200, beat.text
    assert beat.json()["expires_at"] > before  # ISO-8601 strings compare chronologically


async def test_heartbeat_requires_a_device_session(api_client):
    account = await register_account(api_client, label="hb-auth")
    # A web (account) token is not a device — it can't heartbeat a device.
    res = await api_client.post(
        "/devices/heartbeat", headers=bearer(account.token), json={"ttl_seconds": 3600}
    )
    assert res.status_code == 401, res.text


async def test_web_session_deletes_a_device_scoped_to_its_account(api_client):
    account = await register_account(api_client, label="del")
    device = await join_device(api_client, inviter_token=account.token, name="laptop")

    res = await api_client.delete(f"/devices/{device.id}", headers=bearer(account.token))
    assert res.status_code == 204, res.text

    listed = await api_client.get("/devices", headers=bearer(account.token))
    assert all(d["id"] != str(device.id) for d in listed.json())


async def test_cannot_delete_another_accounts_device(api_client):
    mine = await register_account(api_client, label="del-mine")
    theirs = await register_account(api_client, label="del-theirs")
    victim = await join_device(api_client, inviter_token=theirs.token, name="victim")

    res = await api_client.delete(f"/devices/{victim.id}", headers=bearer(mine.token))
    assert res.status_code == 404, res.text
    # Still there for its real owner.
    listed = await api_client.get("/devices", headers=bearer(theirs.token))
    assert any(d["id"] == str(victim.id) for d in listed.json())
