"""Unit tests for AccessRequestService — the handshake broker (issue #69)."""

from uuid import UUID, uuid4

import pytest

from gophkeeper.domain.access_request import AccessRequestStatus
from gophkeeper.domain.device import Device
from gophkeeper.domain.errors import (
    AccessDenied,
    AccessRequestAlreadyPending,
    AccessRequestNotFound,
    AccessRequestNotPending,
    DeviceNotFound,
    NotTrustedWithSecret,
    SecretNotFound,
)
from gophkeeper.domain.secret import Secret
from gophkeeper.services.access_request_service import AccessRequestService
from tests.fakes import FakeUnitOfWork, make_device


async def _setup_owned_secret(uow: FakeUnitOfWork) -> tuple[Device, UUID]:
    owner = make_device()
    await uow.devices.add(owner)
    secret_id = uuid4()
    await uow.secrets.add(Secret(id=secret_id, account_id="acc", ciphertext=b"v1"))
    await uow.access.grant(secret_id, owner.id)
    return owner, secret_id


async def test_device_b_can_request_access():
    uow = FakeUnitOfWork()
    owner, secret_id = await _setup_owned_secret(uow)
    requester = make_device()
    await uow.devices.add(requester)
    service = AccessRequestService(uow)

    request = await service.request(secret_id, device_id=requester.id)

    assert request.status == AccessRequestStatus.PENDING
    assert request.device_id == requester.id
    assert request.secret_id == secret_id
    assert uow.committed is True


async def test_request_by_deactivated_device_denied():
    """The docstring promises 'exist and be active' — a revoked device cannot queue."""
    uow = FakeUnitOfWork()
    owner, secret_id = await _setup_owned_secret(uow)
    requester = make_device(is_active=False)
    await uow.devices.add(requester)
    service = AccessRequestService(uow)

    with pytest.raises(AccessDenied):
        await service.request(secret_id, device_id=requester.id)


async def test_request_by_unknown_device_raises():
    uow = FakeUnitOfWork()
    owner, secret_id = await _setup_owned_secret(uow)
    service = AccessRequestService(uow)

    with pytest.raises(DeviceNotFound):
        await service.request(secret_id, device_id=uuid4())


async def test_request_for_unknown_secret_raises():
    uow = FakeUnitOfWork()
    requester = make_device()
    await uow.devices.add(requester)
    service = AccessRequestService(uow)

    with pytest.raises(SecretNotFound):
        await service.request(uuid4(), device_id=requester.id)


async def test_duplicate_pending_request_rejected():
    uow = FakeUnitOfWork()
    owner, secret_id = await _setup_owned_secret(uow)
    requester = make_device()
    await uow.devices.add(requester)
    service = AccessRequestService(uow)

    await service.request(secret_id, device_id=requester.id)

    with pytest.raises(AccessRequestAlreadyPending):
        await service.request(secret_id, device_id=requester.id)


async def test_only_trusted_device_can_list_pending():
    uow = FakeUnitOfWork()
    owner, secret_id = await _setup_owned_secret(uow)
    requester = make_device()
    stranger = make_device()
    await uow.devices.add(requester)
    await uow.devices.add(stranger)
    service = AccessRequestService(uow)

    await service.request(secret_id, device_id=requester.id)

    with pytest.raises(NotTrustedWithSecret):
        await service.list_pending(secret_id, acting_device_id=stranger.id)

    with pytest.raises(NotTrustedWithSecret):
        await service.list_pending(secret_id, acting_device_id=requester.id)

    pending = await service.list_pending(secret_id, acting_device_id=owner.id)
    assert len(pending) == 1
    assert pending[0].request.device_id == requester.id


async def test_list_pending_carries_requester_public_key():
    """The owner gets the requester's public key in one call, so it can
    re-encrypt without a separate device lookup."""
    uow = FakeUnitOfWork()
    owner, secret_id = await _setup_owned_secret(uow)
    requester = make_device(public_key="REQUESTER-PUBKEY")
    await uow.devices.add(requester)
    service = AccessRequestService(uow)

    await service.request(secret_id, device_id=requester.id)

    pending = await service.list_pending(secret_id, acting_device_id=owner.id)
    assert pending[0].requester_public_key == "REQUESTER-PUBKEY"


async def test_owner_can_approve_and_grant_is_created():
    uow = FakeUnitOfWork()
    owner, secret_id = await _setup_owned_secret(uow)
    requester = make_device()
    await uow.devices.add(requester)
    service = AccessRequestService(uow)

    request = await service.request(secret_id, device_id=requester.id)
    assert not await uow.access.has_access(secret_id, requester.id)

    approved = await service.approve(request.id, acting_device_id=owner.id)

    assert approved.status == AccessRequestStatus.APPROVED
    assert (secret_id, requester.id) in uow.access.grants
    assert uow.committed is True


async def test_non_trusted_device_cannot_approve():
    uow = FakeUnitOfWork()
    owner, secret_id = await _setup_owned_secret(uow)
    requester = make_device()
    await uow.devices.add(requester)
    service = AccessRequestService(uow)

    request = await service.request(secret_id, device_id=requester.id)

    # the requester cannot approve its own request
    with pytest.raises(NotTrustedWithSecret):
        await service.approve(request.id, acting_device_id=requester.id)

    assert not await uow.access.has_access(secret_id, requester.id)


async def test_non_trusted_device_cannot_reject():
    uow = FakeUnitOfWork()
    owner, secret_id = await _setup_owned_secret(uow)
    requester = make_device()
    await uow.devices.add(requester)
    service = AccessRequestService(uow)

    request = await service.request(secret_id, device_id=requester.id)

    with pytest.raises(NotTrustedWithSecret):
        await service.reject(request.id, acting_device_id=requester.id)


async def test_approve_does_not_touch_secret_ciphertext():
    """Zero-Knowledge: approving must not read or modify the ciphertext/version."""
    uow = FakeUnitOfWork()
    owner, secret_id = await _setup_owned_secret(uow)
    requester = make_device()
    await uow.devices.add(requester)
    service = AccessRequestService(uow)

    secret_before = await uow.secrets.get(secret_id)
    ciphertext_before = secret_before.ciphertext
    version_before = secret_before.version

    request = await service.request(secret_id, device_id=requester.id)
    await service.approve(request.id, acting_device_id=owner.id)

    secret_after = await uow.secrets.get(secret_id)
    assert secret_after.ciphertext == ciphertext_before
    assert secret_after.version == version_before


async def test_reject_does_not_create_a_grant():
    uow = FakeUnitOfWork()
    owner, secret_id = await _setup_owned_secret(uow)
    requester = make_device()
    await uow.devices.add(requester)
    service = AccessRequestService(uow)

    request = await service.request(secret_id, device_id=requester.id)
    rejected = await service.reject(request.id, acting_device_id=owner.id)

    assert rejected.status == AccessRequestStatus.REJECTED
    assert not await uow.access.has_access(secret_id, requester.id)
    assert (secret_id, requester.id) not in uow.access.grant_calls
    assert uow.committed is True


async def test_cannot_re_settle_an_approved_request():
    uow = FakeUnitOfWork()
    owner, secret_id = await _setup_owned_secret(uow)
    requester = make_device()
    await uow.devices.add(requester)
    service = AccessRequestService(uow)

    request = await service.request(secret_id, device_id=requester.id)
    await service.approve(request.id, acting_device_id=owner.id)

    with pytest.raises(AccessRequestNotPending):
        await service.approve(request.id, acting_device_id=owner.id)
    with pytest.raises(AccessRequestNotPending):
        await service.reject(request.id, acting_device_id=owner.id)

    # the re-approve attempt must not have written a second grant
    assert uow.access.grant_calls.count((secret_id, requester.id)) == 1


async def test_cannot_re_settle_a_rejected_request():
    uow = FakeUnitOfWork()
    owner, secret_id = await _setup_owned_secret(uow)
    requester = make_device()
    await uow.devices.add(requester)
    service = AccessRequestService(uow)

    request = await service.request(secret_id, device_id=requester.id)
    await service.reject(request.id, acting_device_id=owner.id)

    with pytest.raises(AccessRequestNotPending):
        await service.approve(request.id, acting_device_id=owner.id)
    with pytest.raises(AccessRequestNotPending):
        await service.reject(request.id, acting_device_id=owner.id)

    assert not await uow.access.has_access(secret_id, requester.id)


async def test_approve_unknown_request_raises():
    uow = FakeUnitOfWork()
    await _setup_owned_secret(uow)
    service = AccessRequestService(uow)

    with pytest.raises(AccessRequestNotFound):
        await service.approve(uuid4(), acting_device_id=uuid4())


async def test_reject_unknown_request_raises():
    uow = FakeUnitOfWork()
    await _setup_owned_secret(uow)
    service = AccessRequestService(uow)

    with pytest.raises(AccessRequestNotFound):
        await service.reject(uuid4(), acting_device_id=uuid4())
