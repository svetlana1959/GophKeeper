"""Integration tests for DeviceRepository."""

from uuid import uuid4

import pytest

from gophkeeper.domain.account import Account
from gophkeeper.domain.device import ACTIVE, REVOKED, Device
from gophkeeper.domain.errors import DeviceNotFound
from gophkeeper.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


async def test_store_and_fetch_device(database):
    account_id = uuid4()
    device_id = uuid4()
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
    assert fetched.is_active is True


async def test_rollback_discards_uncommitted_device(database):
    account_id = uuid4()
    device_id = uuid4()
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


async def test_list_for_account_returns_all_statuses(database):
    account_id = uuid4()
    active_id = uuid4()
    revoked_id = uuid4()

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

    by_id = {d.id: d for d in devices}
    assert set(by_id) == {active_id, revoked_id}
    assert by_id[active_id].is_active is True
    assert by_id[revoked_id].is_active is False


async def test_list_for_account_excludes_other_accounts(database):
    account_id = uuid4()
    other_account_id = uuid4()
    async with SqlAlchemyUnitOfWork(database) as uow:
        await uow.accounts.add(Account(id=account_id))
        await uow.accounts.add(Account(id=other_account_id))
        await uow.devices.add(Device(uuid4(), account_id, "mine", "mine-key"))
        await uow.devices.add(Device(uuid4(), other_account_id, "other", "other-key"))
        await uow.commit()

    async with SqlAlchemyUnitOfWork(database) as uow:
        devices = await uow.devices.list_for_account(account_id)

    assert [device.device_name for device in devices] == ["mine"]
