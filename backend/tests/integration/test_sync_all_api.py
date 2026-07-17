"""GET /sync/all — the account-scoped ciphertext read.

Unlike /sync/changes (recipient-scoped), this returns every live secret in the
account regardless of recipient — needed by a client decrypting with the recovery
key, which is a recipient in the ciphertext but not a device. Payloads stay
opaque; the point is that the *set* is account-scoped, not that any caller can
read them.
"""

import base64
from uuid import uuid4

import pytest

from tests.integration.helpers import bearer, join_device, register_account

pytestmark = pytest.mark.integration


async def _push(api_client, token, secret_id, blob, recipients):
    res = await api_client.post(
        "/sync/push",
        headers=bearer(token),
        json={
            "items": [
                {
                    "id": secret_id,
                    "ciphertext_b64": base64.b64encode(blob).decode(),
                    "recipients": recipients,
                }
            ]
        },
    )
    assert res.status_code == 200, res.text


async def test_sync_all_returns_account_secrets_regardless_of_recipient(api_client):
    account = await register_account(api_client, label="sync-all")
    device = await join_device(api_client, inviter_token=account.token, name="laptop")

    sid = str(uuid4())
    # Sealed only to the device — NOT to the account/web caller.
    await _push(api_client, device.token, sid, b"ciphertext-bytes", [device.public_key])

    # The web account session reads it anyway (account-scoped, opaque payload).
    res = await api_client.get("/sync/all", headers=bearer(account.token))
    assert res.status_code == 200, res.text
    got = {s["id"]: s for s in res.json()["secrets"]}
    assert sid in got
    assert got[sid]["ciphertext_b64"] == base64.b64encode(b"ciphertext-bytes").decode()


async def test_sync_all_is_account_scoped(api_client):
    mine = await register_account(api_client, label="sync-all-mine")
    my_device = await join_device(api_client, inviter_token=mine.token, name="mine")
    my_secret = str(uuid4())
    await _push(api_client, my_device.token, my_secret, b"mine", [my_device.public_key])

    theirs = await register_account(api_client, label="sync-all-theirs")
    their_device = await join_device(api_client, inviter_token=theirs.token, name="theirs")
    their_secret = str(uuid4())
    await _push(api_client, their_device.token, their_secret, b"theirs", [their_device.public_key])

    res = await api_client.get("/sync/all", headers=bearer(mine.token))
    ids = {s["id"] for s in res.json()["secrets"]}
    assert my_secret in ids
    assert their_secret not in ids


async def test_sync_all_requires_auth(api_client):
    assert (await api_client.get("/sync/all")).status_code == 401
