"""Integration tests for AccessRequestRepository."""

import asyncio
from uuid import uuid4

import pytest

from gophkeeper.domain.access_request import AccessRequest, AccessRequestStatus
from gophkeeper.domain.device import Device
from gophkeeper.domain.errors import AccessRequestAlreadyPending, AccessRequestNotFound
from gophkeeper.domain.secret import Secret
from gophkeeper.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


async def _make_device_and_secret(uow) -> tuple[object, object]:
    device = Device(id=uuid4(), device_name="d", public_key="pk", is_active=True)
    secret = Secret(id=uuid4(), account_id="acc", ciphertext=b"v1")
    await uow.devices.add(device)
    await uow.secrets.add(secret)
    await uow.commit()
    return device, secret


async def test_add_and_get_request(database):
    async with SqlAlchemyUnitOfWork(database) as uow:
        device, secret = await _make_device_and_secret(uow)

    request_id = uuid4()
    async with SqlAlchemyUnitOfWork(database) as uow:
        await uow.access_requests.add(
            AccessRequest(id=request_id, secret_id=secret.id, device_id=device.id)
        )
        await uow.commit()

    async with SqlAlchemyUnitOfWork(database) as uow:
        fetched = await uow.access_requests.get(request_id)

    assert fetched.status == AccessRequestStatus.PENDING
    assert fetched.secret_id == secret.id
    assert fetched.device_id == device.id


async def test_duplicate_pending_request_raises(database):
    async with SqlAlchemyUnitOfWork(database) as uow:
        device, secret = await _make_device_and_secret(uow)

    async with SqlAlchemyUnitOfWork(database) as uow:
        await uow.access_requests.add(
            AccessRequest(id=uuid4(), secret_id=secret.id, device_id=device.id)
        )
        await uow.commit()

    async with SqlAlchemyUnitOfWork(database) as uow:
        with pytest.raises(AccessRequestAlreadyPending):
            await uow.access_requests.add(
                AccessRequest(id=uuid4(), secret_id=secret.id, device_id=device.id)
            )


async def test_list_pending_for_secret(database):
    async with SqlAlchemyUnitOfWork(database) as uow:
        device, secret = await _make_device_and_secret(uow)

    request_id = uuid4()
    async with SqlAlchemyUnitOfWork(database) as uow:
        await uow.access_requests.add(
            AccessRequest(id=request_id, secret_id=secret.id, device_id=device.id)
        )
        await uow.commit()

    async with SqlAlchemyUnitOfWork(database) as uow:
        pending = await uow.access_requests.list_pending_for_secret(secret.id)

    assert len(pending) == 1
    assert pending[0].id == request_id


async def test_save_persists_status_change(database):
    async with SqlAlchemyUnitOfWork(database) as uow:
        device, secret = await _make_device_and_secret(uow)

    request_id = uuid4()
    async with SqlAlchemyUnitOfWork(database) as uow:
        request = AccessRequest(id=request_id, secret_id=secret.id, device_id=device.id)
        await uow.access_requests.add(request)
        await uow.commit()

    async with SqlAlchemyUnitOfWork(database) as uow:
        request = await uow.access_requests.get(request_id)
        request.approve()
        await uow.access_requests.save(request)
        await uow.commit()

    async with SqlAlchemyUnitOfWork(database) as uow:
        fetched = await uow.access_requests.get(request_id)
        pending = await uow.access_requests.list_pending_for_secret(secret.id)

    assert fetched.status == AccessRequestStatus.APPROVED
    assert pending == []


async def test_get_missing_request_raises(database):
    async with SqlAlchemyUnitOfWork(database) as uow:
        with pytest.raises(AccessRequestNotFound):
            await uow.access_requests.get(uuid4())
        await uow.rollback()


async def test_approving_frees_the_pair_for_a_new_request(database):
    async with SqlAlchemyUnitOfWork(database) as uow:
        device, secret = await _make_device_and_secret(uow)

    first_id = uuid4()
    async with SqlAlchemyUnitOfWork(database) as uow:
        first = AccessRequest(id=first_id, secret_id=secret.id, device_id=device.id)
        await uow.access_requests.add(first)
        await uow.commit()

    async with SqlAlchemyUnitOfWork(database) as uow:
        first = await uow.access_requests.get(first_id)
        first.approve()
        await uow.access_requests.save(first)
        await uow.commit()

    async with SqlAlchemyUnitOfWork(database) as uow:
        second = AccessRequest(id=uuid4(), secret_id=secret.id, device_id=device.id)
        await uow.access_requests.add(second)
        await uow.commit()


async def test_concurrent_inserts_for_same_pair_only_one_succeeds(database):
    """Concurrent inserts must collapse to one row and domain errors."""
    async with SqlAlchemyUnitOfWork(database) as uow:
        device, secret = await _make_device_and_secret(uow)

    async def attempt():
        async with SqlAlchemyUnitOfWork(database) as uow:
            request = AccessRequest(id=uuid4(), secret_id=secret.id, device_id=device.id)
            await uow.access_requests.add(request)
            await uow.commit()

    results = await asyncio.gather(*[attempt() for _ in range(8)], return_exceptions=True)

    successes = [r for r in results if r is None]
    conflicts = [r for r in results if isinstance(r, AccessRequestAlreadyPending)]
    other_exceptions = [
        r
        for r in results
        if isinstance(r, Exception) and not isinstance(r, AccessRequestAlreadyPending)
    ]

    assert other_exceptions == [], f"unexpected exception leaked: {other_exceptions}"
    assert len(successes) == 1, "exactly one concurrent insert should win"
    assert len(conflicts) == 7, "every loser should see a clean domain error, not a crash"

    async with SqlAlchemyUnitOfWork(database) as uow:
        pending = await uow.access_requests.list_pending_for_secret(secret.id)
    assert len(pending) == 1, "the database must end up with exactly one PENDING row"
