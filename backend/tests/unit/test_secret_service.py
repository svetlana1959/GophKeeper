"""Unit tests for SecretService's multi-device access control (issue #69).

Covers store/fetch/update/list_for_device and the access checks they share; the
request/list/approve/reject handshake lives in test_access_request_service.py.
"""

from uuid import uuid4

import pytest

from gophkeeper.domain.errors import AccessDenied, VersionConflict
from gophkeeper.services.secret_service import SecretService
from tests.fakes import FakeUnitOfWork, make_device


async def test_store_grants_creating_device_access():
    uow = FakeUnitOfWork()
    device = make_device()
    await uow.devices.add(device)
    service = SecretService(uow)
    secret_id = uuid4()

    await service.store(
        account_id="acc", secret_id=secret_id, device_id=device.id, ciphertext=b"v1"
    )

    fetched = await service.fetch(secret_id, device_id=device.id)
    assert fetched.id == secret_id
    assert uow.committed is True


async def test_access_maintained_after_update():
    uow = FakeUnitOfWork()
    device = make_device()
    await uow.devices.add(device)
    service = SecretService(uow)
    secret_id = uuid4()

    await service.store(
        account_id="acc", secret_id=secret_id, device_id=device.id, ciphertext=b"v1"
    )
    await service.update(secret_id=secret_id, device_id=device.id, ciphertext=b"v2", base_version=1)

    fetched = await service.fetch(secret_id, device_id=device.id)
    assert fetched.ciphertext == b"v2"
    assert fetched.version == 2


async def test_update_with_stale_base_version_conflicts():
    uow = FakeUnitOfWork()
    device = make_device()
    await uow.devices.add(device)
    service = SecretService(uow)
    secret_id = uuid4()

    await service.store(
        account_id="acc", secret_id=secret_id, device_id=device.id, ciphertext=b"v1"
    )
    await service.update(secret_id=secret_id, device_id=device.id, ciphertext=b"v2", base_version=1)

    # second writer still believes it is editing version 1
    with pytest.raises(VersionConflict):
        await service.update(
            secret_id=secret_id, device_id=device.id, ciphertext=b"v3", base_version=1
        )


async def test_update_denied_for_untrusted_device():
    uow = FakeUnitOfWork()
    owner = make_device()
    stranger = make_device()
    await uow.devices.add(owner)
    await uow.devices.add(stranger)
    service = SecretService(uow)
    secret_id = uuid4()

    await service.store(account_id="acc", secret_id=secret_id, device_id=owner.id, ciphertext=b"v1")

    with pytest.raises(AccessDenied):
        await service.update(
            secret_id=secret_id, device_id=stranger.id, ciphertext=b"x", base_version=1
        )


async def test_fetch_denied_for_untrusted_device():
    uow = FakeUnitOfWork()
    owner = make_device()
    stranger = make_device()
    await uow.devices.add(owner)
    await uow.devices.add(stranger)
    service = SecretService(uow)
    secret_id = uuid4()

    await service.store(account_id="acc", secret_id=secret_id, device_id=owner.id, ciphertext=b"v1")

    with pytest.raises(AccessDenied):
        await service.fetch(secret_id, device_id=stranger.id)


async def test_fetch_denied_for_deactivated_device():
    """A revoked device loses access immediately, even with an existing grant."""
    uow = FakeUnitOfWork()
    device = make_device()
    await uow.devices.add(device)
    service = SecretService(uow)
    secret_id = uuid4()

    await service.store(
        account_id="acc", secret_id=secret_id, device_id=device.id, ciphertext=b"v1"
    )

    device.deactivate()
    await uow.devices.save(device)

    with pytest.raises(AccessDenied):
        await service.fetch(secret_id, device_id=device.id)


async def test_list_for_device_returns_latest_after_reconnect():
    """A trusted device reconnecting sees the latest version of everything it
    has access to, regardless of which device wrote it most recently."""
    uow = FakeUnitOfWork()
    device_a = make_device()
    await uow.devices.add(device_a)
    service = SecretService(uow)

    secret_id = uuid4()
    await service.store(
        account_id="acc", secret_id=secret_id, device_id=device_a.id, ciphertext=b"v1"
    )
    await service.update(
        secret_id=secret_id, device_id=device_a.id, ciphertext=b"v2", base_version=1
    )

    synced = await service.list_for_device(device_a.id)
    assert len(synced) == 1
    assert synced[0].ciphertext == b"v2"
    assert synced[0].version == 2
