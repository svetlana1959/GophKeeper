from uuid import UUID, uuid4

import pytest

from gophkeeper.domain.account import Account
from gophkeeper.domain.device import Device
from gophkeeper.domain.errors import DeviceAlreadyExists, DeviceNotFound
from gophkeeper.services.device_service import DeviceService


class FakeAccountRepository:
    def __init__(self):
        self.accounts: dict[UUID, Account] = {}

    async def add(self, account: Account) -> None:
        self.accounts[account.id] = account

    async def get(self, account_id: UUID) -> Account:
        return self.accounts[account_id]


class FakeDeviceRepository:
    def __init__(self):
        self.devices: dict[UUID, Device] = {}

    async def add(self, device: Device) -> None:
        self.devices[device.id] = device

    async def get(self, device_id: UUID) -> Device:
        if device_id not in self.devices:
            raise DeviceNotFound(device_id)
        return self.devices[device_id]

    async def find_by_public_key(self, public_key: str) -> Device | None:
        return next((d for d in self.devices.values() if d.public_key == public_key), None)

    async def exists(self, device_id: UUID) -> bool:
        return device_id in self.devices

    async def list_for_account(self, account_id: UUID) -> list[Device]:
        return [d for d in self.devices.values() if d.account_id == account_id]

    async def save(self, device: Device) -> None:
        self.devices[device.id] = device


class FakeUnitOfWork:
    def __init__(self):
        self.accounts = FakeAccountRepository()
        self.devices = FakeDeviceRepository()
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def commit(self):
        self.committed = True

    async def rollback(self):
        pass


async def test_register_creates_account_and_active_device():
    uow = FakeUnitOfWork()
    service = DeviceService(uow)

    device = await service.register(
        device_name="MacBook",
        public_key="pubkey",
    )

    assert device.id is not None
    assert device.device_name == "MacBook"
    assert device.public_key == "pubkey"
    assert device.is_active is True
    assert device.account_id in uow.accounts.accounts
    assert uow.committed is True


async def test_register_duplicate_public_key_raises_device_already_exists():
    uow = FakeUnitOfWork()

    existing = Device(
        id=uuid4(),
        account_id=uuid4(),
        device_name="MacBook",
        public_key="pubkey",
    )
    await uow.devices.add(existing)

    service = DeviceService(uow)

    with pytest.raises(DeviceAlreadyExists):
        await service.register(
            device_name="Another Name",
            public_key="pubkey",
        )

    # The duplicate is rejected before any account is created.
    assert uow.accounts.accounts == {}


async def test_fetch_returns_device():
    uow = FakeUnitOfWork()
    device_id = uuid4()

    account_id = uuid4()
    device = Device(
        id=device_id,
        account_id=account_id,
        device_name="MacBook",
        public_key="pubkey",
    )
    await uow.devices.add(device)

    service = DeviceService(uow)

    fetched = await service.fetch(device_id, account_id=account_id)

    assert fetched.id == device_id


async def test_fetch_device_from_other_account_is_not_found():
    uow = FakeUnitOfWork()
    device_id = uuid4()
    device = Device(
        id=device_id,
        account_id=uuid4(),
        device_name="MacBook",
        public_key="pubkey",
    )
    await uow.devices.add(device)

    service = DeviceService(uow)

    with pytest.raises(DeviceNotFound):
        await service.fetch(device_id, account_id=uuid4())


async def test_fetch_missing_device_raises():
    uow = FakeUnitOfWork()
    service = DeviceService(uow)

    with pytest.raises(DeviceNotFound):
        await service.fetch(uuid4(), account_id=uuid4())
