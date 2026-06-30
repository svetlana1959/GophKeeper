"""Unit tests for AccessRequestService."""

from uuid import UUID, uuid4

import pytest

from gophkeeper.domain.access_request import AccessRequest, AccessRequestStatus
from gophkeeper.domain.device import Device
from gophkeeper.domain.errors import (
    AccessRequestAlreadyPending,
    AccessRequestNotPending,
    DeviceNotFound,
    NotSecretOwner,
    SecretNotFound,
)
from gophkeeper.domain.secret import Secret
from gophkeeper.services.access_request_service import AccessRequestService


class FakeDeviceRepository:
    def __init__(self):
        self.devices: dict[UUID, Device] = {}

    async def add(self, device: Device) -> None:
        self.devices[device.id] = device

    async def get(self, device_id: UUID) -> Device:
        if device_id not in self.devices:
            raise DeviceNotFound(device_id)
        return self.devices[device_id]

    async def exists(self, device_id: UUID) -> bool:
        return device_id in self.devices

    async def list_active(self) -> list[Device]:
        return [d for d in self.devices.values() if d.is_active]

    async def save(self, device: Device) -> None:
        self.devices[device.id] = device


class FakeSecretRepository:
    def __init__(self):
        self.secrets: dict[UUID, Secret] = {}

    async def add(self, secret: Secret) -> None:
        self.secrets[secret.id] = secret

    async def get(self, secret_id: UUID) -> Secret:
        if secret_id not in self.secrets:
            raise SecretNotFound(secret_id)
        return self.secrets[secret_id]

    async def list_for_account(self, account_id: str, *, include_deleted: bool = False):
        return [s for s in self.secrets.values() if s.account_id == account_id]

    async def save(self, secret: Secret) -> None:
        self.secrets[secret.id] = secret


class FakeSecretAccessRepository:
    def __init__(self):
        self.grants: set[tuple[UUID, UUID]] = set()
        self.grant_calls: list[tuple[UUID, UUID]] = []

    async def grant(self, secret_id: UUID, device_id: UUID) -> None:
        self.grants.add((secret_id, device_id))
        self.grant_calls.append((secret_id, device_id))

    async def revoke(self, secret_id: UUID, device_id: UUID) -> None:
        self.grants.discard((secret_id, device_id))

    async def has_access(self, secret_id: UUID, device_id: UUID) -> bool:
        return (secret_id, device_id) in self.grants

    async def list_secret_ids_for_device(self, device_id: UUID) -> list[UUID]:
        return [sid for sid, did in self.grants if did == device_id]

    async def list_device_ids_for_secret(self, secret_id: UUID) -> list[UUID]:
        return [did for sid, did in self.grants if sid == secret_id]


class FakeAccessRequestRepository:
    def __init__(self):
        self.requests: dict[UUID, AccessRequest] = {}

    async def add(self, request: AccessRequest) -> None:
        for existing in self.requests.values():
            if (
                existing.secret_id == request.secret_id
                and existing.device_id == request.device_id
                and existing.status == AccessRequestStatus.PENDING
            ):
                raise AccessRequestAlreadyPending(request.secret_id, request.device_id)
        self.requests[request.id] = request

    async def get(self, request_id: UUID) -> AccessRequest:
        if request_id not in self.requests:
            from gophkeeper.domain.errors import AccessRequestNotFound

            raise AccessRequestNotFound(request_id)
        return self.requests[request_id]

    async def list_pending_for_secret(self, secret_id: UUID) -> list[AccessRequest]:
        return [
            r
            for r in self.requests.values()
            if r.secret_id == secret_id and r.status == AccessRequestStatus.PENDING
        ]

    async def save(self, request: AccessRequest) -> None:
        self.requests[request.id] = request


class FakeUnitOfWork:
    def __init__(self):
        self.devices = FakeDeviceRepository()
        self.secrets = FakeSecretRepository()
        self.access = FakeSecretAccessRepository()
        self.access_requests = FakeAccessRequestRepository()
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def commit(self):
        self.committed = True

    async def rollback(self):
        pass


def _device() -> Device:
    return Device(id=uuid4(), device_name="d", public_key="pk", is_active=True)


async def _setup_owned_secret(uow: FakeUnitOfWork) -> tuple[Device, UUID]:
    owner = _device()
    await uow.devices.add(owner)
    secret_id = uuid4()
    await uow.secrets.add(Secret(id=secret_id, account_id="acc", ciphertext=b"v1"))
    await uow.access.grant(secret_id, owner.id)
    return owner, secret_id


async def test_device_b_can_request_access():
    uow = FakeUnitOfWork()
    owner, secret_id = await _setup_owned_secret(uow)
    requester = _device()
    await uow.devices.add(requester)
    service = AccessRequestService(uow)

    request = await service.request(secret_id, device_id=requester.id)

    assert request.status == AccessRequestStatus.PENDING
    assert request.device_id == requester.id
    assert request.secret_id == secret_id


async def test_duplicate_pending_request_rejected():
    uow = FakeUnitOfWork()
    owner, secret_id = await _setup_owned_secret(uow)
    requester = _device()
    await uow.devices.add(requester)
    service = AccessRequestService(uow)

    await service.request(secret_id, device_id=requester.id)

    with pytest.raises(AccessRequestAlreadyPending):
        await service.request(secret_id, device_id=requester.id)


async def test_only_owner_can_list_pending_requests():
    uow = FakeUnitOfWork()
    owner, secret_id = await _setup_owned_secret(uow)
    requester = _device()
    stranger = _device()
    await uow.devices.add(requester)
    await uow.devices.add(stranger)
    service = AccessRequestService(uow)

    await service.request(secret_id, device_id=requester.id)

    with pytest.raises(NotSecretOwner):
        await service.list_pending(secret_id, owner_device_id=stranger.id)

    with pytest.raises(NotSecretOwner):
        await service.list_pending(secret_id, owner_device_id=requester.id)

    pending = await service.list_pending(secret_id, owner_device_id=owner.id)
    assert len(pending) == 1
    assert pending[0].device_id == requester.id


async def test_owner_can_approve_and_grant_is_created():
    uow = FakeUnitOfWork()
    owner, secret_id = await _setup_owned_secret(uow)
    requester = _device()
    await uow.devices.add(requester)
    service = AccessRequestService(uow)

    request = await service.request(secret_id, device_id=requester.id)
    assert not await uow.access.has_access(secret_id, requester.id)

    approved = await service.approve(request.id, owner_device_id=owner.id)

    assert approved.status == AccessRequestStatus.APPROVED
    assert await uow.access.has_access(secret_id, requester.id)
    assert uow.access.grant_calls.count((secret_id, requester.id)) == 1


async def test_non_owner_cannot_approve():
    uow = FakeUnitOfWork()
    owner, secret_id = await _setup_owned_secret(uow)
    requester = _device()
    await uow.devices.add(requester)
    service = AccessRequestService(uow)

    request = await service.request(secret_id, device_id=requester.id)

    with pytest.raises(NotSecretOwner):
        await service.approve(request.id, owner_device_id=requester.id)

    assert not await uow.access.has_access(secret_id, requester.id)


async def test_approve_does_not_touch_secret_ciphertext():
    uow = FakeUnitOfWork()
    owner, secret_id = await _setup_owned_secret(uow)
    requester = _device()
    await uow.devices.add(requester)
    service = AccessRequestService(uow)

    secret_before = await uow.secrets.get(secret_id)
    ciphertext_before = secret_before.ciphertext
    version_before = secret_before.version

    request = await service.request(secret_id, device_id=requester.id)
    await service.approve(request.id, owner_device_id=owner.id)

    secret_after = await uow.secrets.get(secret_id)
    assert secret_after.ciphertext == ciphertext_before
    assert secret_after.version == version_before


async def test_reject_does_not_create_a_grant():
    uow = FakeUnitOfWork()
    owner, secret_id = await _setup_owned_secret(uow)
    requester = _device()
    await uow.devices.add(requester)
    service = AccessRequestService(uow)

    request = await service.request(secret_id, device_id=requester.id)
    rejected = await service.reject(request.id, owner_device_id=owner.id)

    assert rejected.status == AccessRequestStatus.REJECTED
    assert not await uow.access.has_access(secret_id, requester.id)
    assert (secret_id, requester.id) not in uow.access.grant_calls


async def test_cannot_approve_already_settled_request():
    uow = FakeUnitOfWork()
    owner, secret_id = await _setup_owned_secret(uow)
    requester = _device()
    await uow.devices.add(requester)
    service = AccessRequestService(uow)

    request = await service.request(secret_id, device_id=requester.id)
    await service.approve(request.id, owner_device_id=owner.id)

    with pytest.raises(AccessRequestNotPending):
        await service.approve(request.id, owner_device_id=owner.id)

    with pytest.raises(AccessRequestNotPending):
        await service.reject(request.id, owner_device_id=owner.id)
