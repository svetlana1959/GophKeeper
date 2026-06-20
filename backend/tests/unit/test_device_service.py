import pytest

from gophkeeper.domain.device import Device
from gophkeeper.domain.errors import DeviceNotFound, DeviceAlreadyExists
from gophkeeper.services.device_service import DeviceService
from uuid import UUID, uuid4


class FakeDeviceRepository:
    def __init__(self):
        self.devices: dict[str, Device] = {}

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


class FakeUnitOfWork:
    def __init__(self):
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


async def test_register_creates_new_device():
    uow = FakeUnitOfWork()
    service = DeviceService(uow)
    device_id = uuid4()

    device = await service.register(
        device_id=device_id,
        device_name="MacBook",
        public_key="pubkey",
    )

    assert device.id == device_id
    assert device.device_name == "MacBook"
    assert device.public_key == "pubkey"
    assert device.is_active is True
    assert uow.committed is True


async def test_register_duplicate_raises_device_already_exists():
    uow = FakeUnitOfWork()
    device_id = uuid4()

    existing = Device(
        id=device_id,
        device_name="MacBook",
        public_key="pubkey",
        is_active=True,
    )

    await uow.devices.add(existing)

    service = DeviceService(uow)

    with pytest.raises(DeviceAlreadyExists):
        await service.register(
            device_id=device_id,
            device_name="Another Name",
            public_key="another-key",
        )


async def test_fetch_returns_device():
    uow = FakeUnitOfWork()
    device_id = uuid4()

    device = Device(
        id=device_id,
        device_name="MacBook",
        public_key="pubkey",
        is_active=True,
    )

    await uow.devices.add(device)

    service = DeviceService(uow)

    fetched = await service.fetch(device_id)

    assert fetched.id == device_id


async def test_fetch_missing_device_raises():
    uow = FakeUnitOfWork()
    service = DeviceService(uow)

    with pytest.raises(DeviceNotFound):
        await service.fetch(uuid4())
