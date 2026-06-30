"""Unit tests for router functions with fake services.

The endpoints are called directly instead of through TestClient. This keeps
these as unit tests: FastAPI dependency injection, HTTP transport, and the
database are not involved. Each router receives a fake service and is checked
only for delegation and DTO conversion.

Covers device registration/fetching, secret store/list/fetch/update/sync, and
the access-request endpoints.
"""

import base64
from datetime import UTC, datetime
from uuid import UUID, uuid4

from gophkeeper.api.routers.device import fetch_device, register_device
from gophkeeper.api.routers.secrets import (
    approve_secret_access_request,
    fetch_secret,
    list_secret_access_requests,
    list_secrets,
    reject_secret_access_request,
    request_secret_access,
    store_secret,
    sync_secrets,
    update_secret,
)
from gophkeeper.api.schemas.device import RegisterDeviceRequest
from gophkeeper.api.schemas.secrets import StoreSecretRequest, UpdateSecretRequest
from gophkeeper.api.schemas.sync import SyncRequest
from gophkeeper.domain.access_request import AccessRequest, AccessRequestStatus
from gophkeeper.domain.device import Device
from gophkeeper.domain.secret import Secret
from gophkeeper.domain.sync import SyncOutcome, SyncReport, SyncResult, SyncStatus


class FakeDeviceService:
    def __init__(self, device: Device) -> None:
        self.device = device
        self.register_calls: list[tuple[UUID, str, str]] = []
        self.fetch_calls: list[UUID] = []

    async def register(self, *, device_id: UUID, device_name: str, public_key: str) -> Device:
        self.register_calls.append((device_id, device_name, public_key))
        return self.device

    async def fetch(self, device_id: UUID) -> Device:
        self.fetch_calls.append(device_id)
        return self.device


class FakeSecretService:
    def __init__(self, secret: Secret) -> None:
        self.secret = secret
        self.store_calls: list[dict[str, object]] = []
        self.list_calls: list[UUID] = []
        self.fetch_calls: list[tuple[UUID, UUID]] = []
        self.update_calls: list[dict[str, object]] = []

    async def store(
        self,
        *,
        account_id: str,
        secret_id: UUID,
        device_id: UUID,
        ciphertext: bytes,
    ) -> Secret:
        self.store_calls.append(
            {
                "account_id": account_id,
                "secret_id": secret_id,
                "device_id": device_id,
                "ciphertext": ciphertext,
            }
        )
        return self.secret

    async def list_for_device(self, device_id: UUID) -> list[Secret]:
        self.list_calls.append(device_id)
        return [self.secret]

    async def fetch(self, secret_id: UUID, *, device_id: UUID) -> Secret:
        self.fetch_calls.append((secret_id, device_id))
        return self.secret

    async def update(
        self,
        *,
        secret_id: UUID,
        device_id: UUID,
        ciphertext: bytes,
        base_version: int,
    ) -> Secret:
        self.update_calls.append(
            {
                "secret_id": secret_id,
                "device_id": device_id,
                "ciphertext": ciphertext,
                "base_version": base_version,
            }
        )
        return self.secret


class FakeSyncService:
    def __init__(self, report: SyncReport) -> None:
        self.report = report
        self.calls: list[tuple[UUID, object]] = []

    async def sync(self, *, device_id: UUID, client_state: object) -> SyncReport:
        self.calls.append((device_id, client_state))
        return self.report


class FakeAccessRequestService:
    def __init__(self, access_request: AccessRequest) -> None:
        self._access_request = access_request
        self.request_calls: list[tuple[UUID, UUID]] = []
        self.list_calls: list[tuple[UUID, UUID]] = []
        self.approve_calls: list[tuple[UUID, UUID]] = []
        self.reject_calls: list[tuple[UUID, UUID]] = []

    async def request(self, secret_id: UUID, *, device_id: UUID) -> AccessRequest:
        self.request_calls.append((secret_id, device_id))
        return self._access_request

    async def list_pending(self, secret_id: UUID, *, owner_device_id: UUID) -> list[AccessRequest]:
        self.list_calls.append((secret_id, owner_device_id))
        return [self._access_request]

    async def approve(self, request_id: UUID, *, owner_device_id: UUID) -> AccessRequest:
        self.approve_calls.append((request_id, owner_device_id))
        return self._access_request

    async def reject(self, request_id: UUID, *, owner_device_id: UUID) -> AccessRequest:
        self.reject_calls.append((request_id, owner_device_id))
        return self._access_request


def _device() -> Device:
    return Device(id=uuid4(), device_name="MacBook", public_key="public-key", is_active=True)


def _secret() -> Secret:
    return Secret(
        id=uuid4(),
        account_id="account-1",
        ciphertext=b"ciphertext",
        updated_at=datetime(2026, 6, 30, 12, 0, tzinfo=UTC),
    )


async def test_device_router_delegates_registration_and_fetch_to_fake_service() -> None:
    device = _device()
    service = FakeDeviceService(device)
    body = RegisterDeviceRequest(
        id=device.id,
        device_name=device.device_name,
        public_key=device.public_key,
    )

    registered = await register_device(body=body, service=service)
    fetched = await fetch_device(device_id=device.id, service=service)

    assert registered.id == device.id
    assert fetched.public_key == "public-key"
    assert service.register_calls == [(device.id, "MacBook", "public-key")]
    assert service.fetch_calls == [device.id]


async def test_secret_routes_delegate_store_list_fetch_and_update_to_fake_service() -> None:
    """The router only converts request/response data; service logic stays out of it."""
    secret = _secret()
    device_id = uuid4()
    service = FakeSecretService(secret)
    stored_body = StoreSecretRequest(
        id=secret.id,
        account_id=secret.account_id,
        ciphertext_b64=base64.b64encode(b"ciphertext").decode("ascii"),
    )
    update_body = UpdateSecretRequest(
        ciphertext_b64=base64.b64encode(b"next-ciphertext").decode("ascii"),
        base_version=1,
    )

    stored = await store_secret(body=stored_body, device_id=device_id, service=service)
    listed = await list_secrets(device_id=device_id, service=service)
    fetched = await fetch_secret(secret_id=secret.id, device_id=device_id, service=service)
    updated = await update_secret(
        secret_id=secret.id,
        body=update_body,
        device_id=device_id,
        service=service,
    )

    assert stored.id == secret.id
    assert listed == [stored]
    assert fetched.ciphertext_b64 == stored.ciphertext_b64
    assert updated.version == 1
    assert service.store_calls[0]["ciphertext"] == b"ciphertext"
    assert service.list_calls == [device_id]
    assert service.fetch_calls == [(secret.id, device_id)]
    assert service.update_calls[0]["ciphertext"] == b"next-ciphertext"
    assert service.update_calls[0]["base_version"] == 1


async def test_sync_route_converts_client_state_before_calling_fake_service() -> None:
    secret = _secret()
    device_id = uuid4()
    report = SyncReport(
        status=SyncStatus.OK,
        results=[
            SyncResult(
                secret_id=secret.id,
                outcome=SyncOutcome.NEW,
                version=secret.version,
                ciphertext=secret.ciphertext,
                updated_at=secret.updated_at,
            )
        ],
    )
    service = FakeSyncService(report)
    body = SyncRequest(client_state=[{"id": secret.id, "version": 0}])

    response = await sync_secrets(body=body, device_id=device_id, service=service)

    assert response.status == "OK"
    assert response.results[0].outcome == "NEW"
    assert service.calls[0][0] == device_id
    assert service.calls[0][1][0].id == secret.id
    assert service.calls[0][1][0].version == 0


async def test_access_request_routes_delegate_each_handshake_action_to_fake_service() -> None:
    secret_id = uuid4()
    device_id = uuid4()
    request = AccessRequest(
        id=uuid4(),
        secret_id=secret_id,
        device_id=uuid4(),
        status=AccessRequestStatus.PENDING,
    )
    service = FakeAccessRequestService(request)

    created = await request_secret_access(
        secret_id=secret_id,
        device_id=device_id,
        service=service,
    )
    pending = await list_secret_access_requests(
        secret_id=secret_id,
        device_id=device_id,
        service=service,
    )
    approved = await approve_secret_access_request(
        request_id=request.id,
        device_id=device_id,
        service=service,
    )
    rejected = await reject_secret_access_request(
        request_id=request.id,
        device_id=device_id,
        service=service,
    )

    assert created.status == "PENDING"
    assert pending == [created]
    assert approved.id == request.id
    assert rejected.id == request.id
    assert service.request_calls == [(secret_id, device_id)]
    assert service.list_calls == [(secret_id, device_id)]
    assert service.approve_calls == [(request.id, device_id)]
    assert service.reject_calls == [(request.id, device_id)]
