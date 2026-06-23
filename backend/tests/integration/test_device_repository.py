"""Integration tests for DeviceRepository."""

import pytest

from gophkeeper.domain.device import Device
from gophkeeper.domain.errors import DeviceNotFound
from gophkeeper.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from uuid import uuid4

pytestmark = pytest.mark.integration


async def test_store_and_fetch_device(database):
    device_id = uuid4()
    async with SqlAlchemyUnitOfWork(database) as uow:
        await uow.devices.add(
            Device(
                id=device_id,
                device_name="laptop",
                public_key="age1testpublickey",
                is_active=True,
            )
        )
        await uow.commit()

    async with SqlAlchemyUnitOfWork(database) as uow:
        fetched = await uow.devices.get(device_id)

    assert fetched.device_name == "laptop"
    assert fetched.public_key == "age1testpublickey"
    assert fetched.is_active is True


async def test_rollback_discards_uncommitted_device(database):
    device_id = uuid4()
    async with SqlAlchemyUnitOfWork(database) as uow:
        await uow.devices.add(
            Device(
                id=device_id,
                device_name="phone",
                public_key="age1phonekey",
                is_active=True,
            )
        )
        await uow.rollback()

    async with SqlAlchemyUnitOfWork(database) as uow:
        with pytest.raises(DeviceNotFound):
            await uow.devices.get(device_id)


async def test_list_active_devices(database):
    active_id = uuid4()
    inactive_id = uuid4()

    async with SqlAlchemyUnitOfWork(database) as uow:
        await uow.devices.add(
            Device(
                id=active_id,
                device_name="laptop",
                public_key="key1",
                is_active=True,
            )
        )

        await uow.devices.add(
            Device(
                id=inactive_id,
                device_name="phone",
                public_key="key2",
                is_active=False,
            )
        )

        await uow.commit()

    async with SqlAlchemyUnitOfWork(database) as uow:
        devices = await uow.devices.list_active()

    assert len(devices) == 1
    assert devices[0].id == active_id

