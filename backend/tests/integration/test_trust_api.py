"""Full-stack coverage for the device trust log.

The server relays and orders signed vouch/revoke certs but never verifies their
signatures — so these tests drive the transport, not the crypto: a device may
publish only its own certs, seq must be contiguous per issuer, and pulls are
ordered and account-scoped. Signatures are opaque strings here (the client, not
the server, verifies them). Exercises the trust router and all three repository
queries (add / max_issuer_seq / list_since) end to end.
"""

import json
from uuid import uuid4

import pytest

from tests.integration.helpers import DeviceSession, bearer, join_device, register_account

pytestmark = pytest.mark.integration


def _cert_body(
    device: DeviceSession,
    *,
    seq: int,
    kind: str = "vouch",
    issuer_id: str | None = None,
    account_id: str | None = None,
    **overrides,
) -> dict:
    """A well-formed cert body issued by `device`. The signature is opaque."""
    body = {
        "kind": kind,
        "account_id": account_id or str(device.account_id),
        "issuer_id": issuer_id or str(device.id),
        "seq": seq,
        "issued_at": 1_700_000_000 + seq,
        "sig": f"sig-{seq}",
    }
    body.update(overrides)
    return body


async def _publish(api_client, device: DeviceSession, body: dict):
    return await api_client.post("/trust/certs", headers=bearer(device.token), json=body)


async def test_publish_then_pull_returns_certs_in_order(api_client):
    account = await register_account(api_client, label="trust")
    device = await join_device(api_client, inviter_token=account.token, name="issuer")

    published = await _publish(api_client, device, _cert_body(device, seq=0, kind="vouch"))
    assert published.status_code == 201
    assert published.json()["seq"] == 0
    assert published.json()["kind"] == "vouch"
    assert (
        await _publish(api_client, device, _cert_body(device, seq=1, kind="revoke"))
    ).status_code == 201

    pull = await api_client.get("/trust/certs", params={"since": 0}, headers=bearer(device.token))
    assert pull.status_code == 200
    body = pull.json()
    assert [c["seq"] for c in body["certs"]] == [0, 1]
    assert [c["kind"] for c in body["certs"]] == ["vouch", "revoke"]
    cursor = body["cursor"]
    assert cursor > 0

    # Nothing new past the cursor.
    tail = await api_client.get(
        "/trust/certs", params={"since": cursor}, headers=bearer(device.token)
    )
    assert tail.json()["certs"] == []
    assert tail.json()["cursor"] == cursor


async def test_publish_rejects_non_contiguous_seq(api_client):
    account = await register_account(api_client, label="trust-seq")
    device = await join_device(api_client, inviter_token=account.token, name="issuer")

    assert (await _publish(api_client, device, _cert_body(device, seq=0))).status_code == 201
    # A gap (expected 1, got 2) is refused...
    assert (await _publish(api_client, device, _cert_body(device, seq=2))).status_code == 409
    # ...and so is a rewind/duplicate (expected 1, got 0).
    assert (await _publish(api_client, device, _cert_body(device, seq=0))).status_code == 409
    # The correct next seq is accepted.
    assert (await _publish(api_client, device, _cert_body(device, seq=1))).status_code == 201


async def test_device_may_only_publish_its_own_certs(api_client):
    account = await register_account(api_client, label="trust-guard")
    device = await join_device(api_client, inviter_token=account.token, name="issuer")
    other = await join_device(api_client, inviter_token=account.token, name="other")

    spoofed_issuer = await _publish(
        api_client, device, _cert_body(device, seq=0, issuer_id=str(other.id))
    )
    assert spoofed_issuer.status_code == 401

    foreign_account = await _publish(
        api_client, device, _cert_body(device, seq=0, account_id=str(uuid4()))
    )
    assert foreign_account.status_code == 401


async def test_trust_log_is_account_scoped(api_client):
    first_account = await register_account(api_client, label="trust-a")
    first_device = await join_device(api_client, inviter_token=first_account.token, name="a-dev")
    second_account = await register_account(api_client, label="trust-b")
    second_device = await join_device(api_client, inviter_token=second_account.token, name="b-dev")

    await _publish(api_client, first_device, _cert_body(first_device, seq=0))
    await _publish(api_client, second_device, _cert_body(second_device, seq=0))

    pull = await api_client.get(
        "/trust/certs", params={"since": 0}, headers=bearer(first_device.token)
    )
    certs = pull.json()["certs"]
    assert len(certs) == 1
    assert certs[0]["issuer_id"] == str(first_device.id)
    # The other account's device never appears in this account's log.
    assert str(second_device.id) not in json.dumps(pull.json())


async def test_each_issuer_has_an_independent_seq_space(api_client):
    account = await register_account(api_client, label="trust-multi")
    first = await join_device(api_client, inviter_token=account.token, name="first")
    second = await join_device(api_client, inviter_token=first.token, name="second")

    # Two devices in one account each start their own chain at 0.
    assert (await _publish(api_client, first, _cert_body(first, seq=0))).status_code == 201
    assert (await _publish(api_client, second, _cert_body(second, seq=0))).status_code == 201

    pull = await api_client.get("/trust/certs", params={"since": 0}, headers=bearer(first.token))
    assert {c["issuer_id"] for c in pull.json()["certs"]} == {str(first.id), str(second.id)}
