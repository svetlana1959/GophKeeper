from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from gophkeeper.domain.device import Device
from gophkeeper.domain.errors import DeviceAlreadyExists, InvalidInvite
from gophkeeper.domain.invite import Invite
from gophkeeper.services.enrollment_service import EnrollmentService, _hash_code


class FakeInviteRepository:
    def __init__(self):
        self.invites: dict[str, Invite] = {}  # keyed by code_hash

    async def add(self, invite: Invite) -> None:
        self.invites[invite.code_hash] = invite

    async def find_by_code_hash(self, code_hash: str) -> Invite | None:
        return self.invites.get(code_hash)

    async def save(self, invite: Invite) -> None:
        self.invites[invite.code_hash] = invite


class FakeDeviceRepository:
    def __init__(self):
        self.devices: dict[UUID, Device] = {}

    async def add(self, device: Device) -> None:
        self.devices[device.id] = device

    async def find_by_public_key(self, public_key: str) -> Device | None:
        return next((d for d in self.devices.values() if d.public_key == public_key), None)


class FakeUnitOfWork:
    def __init__(self):
        self.invites = FakeInviteRepository()
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


async def test_invite_then_join_admits_device():
    uow = FakeUnitOfWork()
    service = EnrollmentService(uow)
    account_id = uuid4()

    invite, code = await service.create_invite(account_id=account_id)
    assert code  # plaintext returned once
    assert invite.code_hash != code  # only the hash is stored

    device = await service.join(code=code, device_name="phone", public_key="age1new")
    assert device.account_id == account_id
    assert device.is_active is True
    # The invite is now consumed.
    assert uow.invites.invites[invite.code_hash].consumed_at is not None


async def test_join_with_bad_code_rejected():
    uow = FakeUnitOfWork()
    service = EnrollmentService(uow)
    with pytest.raises(InvalidInvite):
        await service.join(code="nope", device_name="x", public_key="age1x")


async def test_join_with_consumed_code_rejected():
    uow = FakeUnitOfWork()
    service = EnrollmentService(uow)
    _, code = await service.create_invite(account_id=uuid4())

    await service.join(code=code, device_name="first", public_key="age1a")
    with pytest.raises(InvalidInvite):
        await service.join(code=code, device_name="second", public_key="age1b")


async def test_join_with_expired_code_rejected():
    uow = FakeUnitOfWork()
    code = "expired-code"
    expired = Invite(
        id=uuid4(),
        account_id=uuid4(),
        code_hash=_hash_code(code),
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    uow.invites.invites[expired.code_hash] = expired

    service = EnrollmentService(uow)
    with pytest.raises(InvalidInvite):
        await service.join(code=code, device_name="x", public_key="age1x")


async def test_join_duplicate_public_key_rejected():
    uow = FakeUnitOfWork()
    service = EnrollmentService(uow)
    _, code1 = await service.create_invite(account_id=uuid4())
    await service.join(code=code1, device_name="a", public_key="age1dup")

    _, code2 = await service.create_invite(account_id=uuid4())
    with pytest.raises(DeviceAlreadyExists):
        await service.join(code=code2, device_name="b", public_key="age1dup")
