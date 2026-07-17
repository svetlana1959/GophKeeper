"""Domain errors must surface as the right HTTP status.

Unit tests prove the services *raise* these errors; only a full-stack test proves
the exception handlers map them to a status code (a miss would otherwise become a
500). This is wiring the fakes can't reach — the mapping lives in
``gophkeeper.api.errors`` and is exercised only through a real request.
"""

from uuid import uuid4

import pytest
from pyrage import x25519

from tests.integration.helpers import (
    bearer,
    create_invite,
    join_device,
    join_with_code,
    register_account,
    set_recovery_key,
)

pytestmark = pytest.mark.integration


async def test_duplicate_email_is_conflict(api_client):
    email = f"dup-{uuid4()}@example.test"
    first = await api_client.post("/accounts", json={"email": email, "password": "hunter2secret"})
    assert first.status_code == 201

    second = await api_client.post("/accounts", json={"email": email, "password": "different-pw"})
    assert second.status_code == 409
    assert "detail" in second.json()


async def test_second_recovery_key_is_conflict(api_client):
    account = await register_account(api_client, label="recovery-conflict")

    first = await set_recovery_key(api_client, token=account.token, pubkey="age1first")
    assert first.status_code == 200
    assert first.json()["recovery_pubkey"] == "age1first"

    second = await set_recovery_key(api_client, token=account.token, pubkey="age1second")
    assert second.status_code == 409
    # The original key is untouched — the write-once guard, end to end.
    me = await api_client.get("/accounts/me", headers=bearer(account.token))
    assert me.json()["recovery_pubkey"] == "age1first"


async def test_join_with_unknown_code_is_bad_request(api_client):
    identity = x25519.Identity.generate()
    join = await join_with_code(
        api_client,
        code_hash="0" * 64,  # a well-formed hash that matches no invite
        name="orphan",
        public_key=str(identity.to_public()),
    )
    assert join.status_code == 400
    assert "detail" in join.json()


async def test_joining_twice_with_the_same_key_is_conflict(api_client):
    account = await register_account(api_client, label="dup-device")
    identity = x25519.Identity.generate()

    await join_device(api_client, inviter_token=account.token, name="original", identity=identity)

    # A second, valid invite — but the same device public key is already enrolled.
    code_hash = await create_invite(api_client, inviter_token=account.token)
    duplicate = await join_with_code(
        api_client, code_hash=code_hash, name="clone", public_key=str(identity.to_public())
    )
    assert duplicate.status_code == 409
    assert "detail" in duplicate.json()


async def test_fetching_unknown_device_is_not_found(api_client):
    account = await register_account(api_client, label="missing-device")
    device = await join_device(api_client, inviter_token=account.token, name="real")

    response = await api_client.get(f"/devices/{uuid4()}", headers=bearer(device.token))
    assert response.status_code == 404
    assert "detail" in response.json()


async def test_polling_unknown_invite_is_not_found(api_client):
    account = await register_account(api_client, label="missing-invite")

    response = await api_client.get(f"/enroll/invite/{uuid4()}", headers=bearer(account.token))
    assert response.status_code == 404
    assert "detail" in response.json()
