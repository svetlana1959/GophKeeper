"""Integration tests for DeviceRepository."""

from uuid import uuid4

import pytest

from gophkeeper.domain.account import Account
from gophkeeper.domain.device import ACTIVE, REVOKED, Device
from gophkeeper.domain.errors import DeviceNotFound
from gophkeeper.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


async def test_store_and_fetch_device(database):
    device_id = uuid4()
    account_id = uuid4()
    async with SqlAlchemyUnitOfWork(database) as uow:
        await uow.accounts.add(Account(id=account_id))
        await uow.devices.add(
            Device(
                id=device_id,
                account_id=account_id,
                device_name="laptop",
                public_key="age1testpublickey",
                status=ACTIVE,
            )
        )
        await uow.commit()

    async with SqlAlchemyUnitOfWork(database) as uow:
        fetched = await uow.devices.get(device_id)

    assert fetched.device_name == "laptop"
    assert fetched.public_key == "age1testpublickey"
    assert fetched.account_id == account_id
    assert fetched.status == ACTIVE
    assert fetched.last_seen_at is None


async def test_save_persists_revoked_status(database):
    device_id = uuid4()
    account_id = uuid4()
    async with SqlAlchemyUnitOfWork(database) as uow:
        await uow.accounts.add(Account(id=account_id))
        await uow.devices.add(
            Device(
                id=device_id,
                account_id=account_id,
                device_name="laptop",
                public_key="age1revokeddevice",
                status=ACTIVE,
            )
        )
        await uow.commit()

    async with SqlAlchemyUnitOfWork(database) as uow:
        device = await uow.devices.get(device_id)
        device.revoke()
        await uow.devices.save(device)
        await uow.commit()

    async with SqlAlchemyUnitOfWork(database) as uow:
        fetched = await uow.devices.get(device_id)

    assert fetched.status == REVOKED
    assert fetched.may_authenticate() is False


async def test_rollback_discards_uncommitted_device(database):
    device_id = uuid4()
    account_id = uuid4()
    async with SqlAlchemyUnitOfWork(database) as uow:
        await uow.accounts.add(Account(id=account_id))
        await uow.devices.add(
            Device(
                id=device_id,
                account_id=account_id,
                device_name="phone",
                public_key="age1phonekey",
                status=ACTIVE,
            )
        )
        await uow.rollback()

    async with SqlAlchemyUnitOfWork(database) as uow:
        with pytest.raises(DeviceNotFound):
            await uow.devices.get(device_id)


async def test_list_devices_for_account_includes_all_statuses(database):
    active_id = uuid4()
    revoked_id = uuid4()
    account_id = uuid4()

    async with SqlAlchemyUnitOfWork(database) as uow:
        await uow.accounts.add(Account(id=account_id))
        await uow.devices.add(
            Device(
                id=active_id,
                account_id=account_id,
                device_name="laptop",
                public_key="key1",
                status=ACTIVE,
            )
        )
        await uow.devices.add(
            Device(
                id=revoked_id,
                account_id=account_id,
                device_name="phone",
                public_key="key2",
                status=REVOKED,
            )
        )
        await uow.commit()

    async with SqlAlchemyUnitOfWork(database) as uow:
        devices = await uow.devices.list_for_account(account_id)

    assert [(device.id, device.status) for device in devices] == [
        (active_id, ACTIVE),
        (revoked_id, REVOKED),
    ]
