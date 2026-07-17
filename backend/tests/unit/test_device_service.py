from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from gophkeeper.domain.account import Account
from gophkeeper.domain.device import Device
from gophkeeper.domain.errors import DeviceNotFound
from gophkeeper.services.device_service import DeviceService, capped_expiry
from gophkeeper.settings.settings import settings


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

    async def delete_expired(self, *, now: datetime) -> int:
        expired = [
            d.id
            for d in self.devices.values()
            if d.expires_at is not None and d.expires_at < now
        ]
        for device_id in expired:
            del self.devices[device_id]
        return len(expired)


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


def test_capped_expiry_caps_at_max_and_none_never_expires():
    assert capped_expiry(None) is None
    now = datetime.now(UTC)
    huge = capped_expiry(10**9, now=now)  # ~31 years, far over the cap
    assert huge == now + timedelta(seconds=settings.security.device_max_ttl_seconds)
    modest = capped_expiry(3600, now=now)
    assert modest == now + timedelta(seconds=3600)


async def test_heartbeat_extends_expiry():
    uow = FakeUnitOfWork()
    account_id = uuid4()
    device = Device(
        id=uuid4(),
        account_id=account_id,
        device_name="Firefox on Linux",
        public_key="age1web",
        expires_at=datetime.now(UTC) + timedelta(seconds=10),
    )
    await uow.devices.add(device)

    updated = await DeviceService(uow).heartbeat(
        device.id, account_id=account_id, ttl_seconds=3600
    )

    assert updated.expires_at is not None
    assert updated.expires_at > datetime.now(UTC) + timedelta(seconds=3000)
    assert uow.committed


async def test_heartbeat_on_other_account_is_not_found():
    uow = FakeUnitOfWork()
    device = Device(
        id=uuid4(),
        account_id=uuid4(),
        device_name="Firefox on Linux",
        public_key="age1web",
    )
    await uow.devices.add(device)

    with pytest.raises(DeviceNotFound):
        await DeviceService(uow).heartbeat(device.id, account_id=uuid4(), ttl_seconds=3600)


async def test_reap_expired_deletes_only_past_devices():
    uow = FakeUnitOfWork()
    account_id = uuid4()
    now = datetime.now(UTC)
    expired = Device(
        id=uuid4(),
        account_id=account_id,
        device_name="stale browser",
        public_key="age1stale",
        expires_at=now - timedelta(hours=1),
    )
    live = Device(
        id=uuid4(),
        account_id=account_id,
        device_name="fresh browser",
        public_key="age1fresh",
        expires_at=now + timedelta(hours=1),
    )
    never = Device(
        id=uuid4(),
        account_id=account_id,
        device_name="cli",
        public_key="age1cli",
    )
    for d in (expired, live, never):
        await uow.devices.add(d)

    reaped = await DeviceService(uow).reap_expired(now=now)

    assert reaped == 1
    assert expired.id not in uow.devices.devices
    assert live.id in uow.devices.devices
    assert never.id in uow.devices.devices
    assert uow.committed
