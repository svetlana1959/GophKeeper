"""API-level tests for the secrets/access-request endpoints.

These exercise the real router, the ``X-Device-Id`` dependency, and the
domain-error -> HTTP-status mapping, against a fake Unit of Work injected via
``app.dependency_overrides``. State is seeded directly (synchronously) so the
test stays sync and can use the standard ``TestClient``.
"""

from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from gophkeeper.api.deps import get_uow
from gophkeeper.api.errors import register_exception_handlers
from gophkeeper.api.routers import secrets
from gophkeeper.domain.secret import Secret
from tests.fakes import FakeUnitOfWork, make_device


def _build() -> tuple[TestClient, FakeUnitOfWork]:
    fake = FakeUnitOfWork()
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(secrets.router)
    app.dependency_overrides[get_uow] = lambda: fake
    return TestClient(app), fake


def _seed_owned_secret(fake: FakeUnitOfWork):
    owner = make_device()
    fake.devices.devices[owner.id] = owner
    secret = Secret(id=uuid4(), account_id="acc", ciphertext=b"v1")
    fake.secrets.secrets[secret.id] = secret
    fake.access.grants.add((secret.id, owner.id))
    return owner, secret


def _add_device(fake: FakeUnitOfWork, **kwargs):
    device = make_device(**kwargs)
    fake.devices.devices[device.id] = device
    return device


def test_full_handshake_request_list_approve():
    client, fake = _build()
    owner, secret = _seed_owned_secret(fake)
    requester = _add_device(fake, public_key="REQUESTER-PUBKEY")

    # Device B asks for access.
    created = client.post(
        f"/secrets/{secret.id}/requests", headers={"X-Device-Id": str(requester.id)}
    )
    assert created.status_code == 201
    request_id = created.json()["id"]

    # Device A reads the queue and gets the requester's public key in one call.
    listed = client.get(f"/secrets/{secret.id}/requests", headers={"X-Device-Id": str(owner.id)})
    assert listed.status_code == 200
    body = listed.json()
    assert len(body) == 1
    assert body[0]["device_id"] == str(requester.id)
    assert body[0]["public_key"] == "REQUESTER-PUBKEY"

    # Device A approves -> the grant exists.
    approved = client.post(
        f"/secrets/requests/{request_id}/approve", headers={"X-Device-Id": str(owner.id)}
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"
    assert (secret.id, requester.id) in fake.access.grants


def test_reject_creates_no_grant():
    client, fake = _build()
    owner, secret = _seed_owned_secret(fake)
    requester = _add_device(fake)

    created = client.post(
        f"/secrets/{secret.id}/requests", headers={"X-Device-Id": str(requester.id)}
    )
    request_id = created.json()["id"]

    rejected = client.post(
        f"/secrets/requests/{request_id}/reject", headers={"X-Device-Id": str(owner.id)}
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "REJECTED"
    assert (secret.id, requester.id) not in fake.access.grants


def test_missing_device_header_is_400():
    client, fake = _build()
    _, secret = _seed_owned_secret(fake)

    resp = client.post(f"/secrets/{secret.id}/requests")
    assert resp.status_code == 400


@pytest.mark.parametrize(
    "scenario,expected",
    [("unknown_secret", 404), ("untrusted_list", 403), ("duplicate_request", 409)],
)
def test_domain_errors_map_to_status_codes(scenario: str, expected: int):
    client, fake = _build()
    owner, secret = _seed_owned_secret(fake)
    requester = _add_device(fake)

    if scenario == "unknown_secret":
        resp = client.post(
            f"/secrets/{uuid4()}/requests", headers={"X-Device-Id": str(requester.id)}
        )
    elif scenario == "untrusted_list":
        stranger = _add_device(fake)
        resp = client.get(
            f"/secrets/{secret.id}/requests", headers={"X-Device-Id": str(stranger.id)}
        )
    else:  # duplicate_request
        client.post(f"/secrets/{secret.id}/requests", headers={"X-Device-Id": str(requester.id)})
        resp = client.post(
            f"/secrets/{secret.id}/requests", headers={"X-Device-Id": str(requester.id)}
        )

    assert resp.status_code == expected
