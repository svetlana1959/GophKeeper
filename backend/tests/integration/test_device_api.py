"""Full-stack coverage for the account-scoped device list.

`GET /devices` is account-scoped and now accepts a web (account) session as well
as a device session — the web needs the device list to show your devices and to
drive device approval. It stays scoped to the caller's account and never leaks
another account's devices.
"""

import pytest

from tests.integration.helpers import bearer, join_device, register_account

pytestmark = pytest.mark.integration


async def test_web_account_session_lists_its_devices(api_client):
    account = await register_account(api_client, label="dev-list")
    first = await join_device(api_client, inviter_token=account.token, name="laptop")
    second = await join_device(api_client, inviter_token=first.token, name="phone")

    # The web holds an ACCOUNT token (no device token), yet can read the list.
    response = await api_client.get("/devices", headers=bearer(account.token))
    assert response.status_code == 200, response.text

    by_id = {d["id"]: d for d in response.json()}
    assert set(by_id) == {str(first.id), str(second.id)}
    assert by_id[str(first.id)]["device_name"] == "laptop"
    assert by_id[str(first.id)]["status"] == "active"


async def test_device_list_is_account_scoped(api_client):
    mine = await register_account(api_client, label="dev-mine")
    my_device = await join_device(api_client, inviter_token=mine.token, name="mine")
    theirs = await register_account(api_client, label="dev-theirs")
    their_device = await join_device(api_client, inviter_token=theirs.token, name="theirs")

    response = await api_client.get("/devices", headers=bearer(mine.token))
    ids = {d["id"] for d in response.json()}
    assert ids == {str(my_device.id)}
    assert str(their_device.id) not in ids


async def test_device_list_requires_auth(api_client):
    assert (await api_client.get("/devices")).status_code == 401
