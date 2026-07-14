from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from gophkeeper.domain.device import Device
from gophkeeper.domain.errors import DeviceAlreadyExists, InvalidInvite, InviteNotFound
from gophkeeper.domain.invite import Invite
from gophkeeper.services.enrollment_service import EnrollmentService


class FakeInviteRepository:
    def __init__(self):
        self.invites: dict[str, Invite] = {}  # keyed by code_hash

    async def add(self, invite: Invite) -> None:
        self.invites[invite.code_hash] = invite

    async def find_by_code_hash(self, code_hash: str) -> Invite | None:
        return self.invites.get(code_hash)

    async def find_by_id(self, invite_id: UUID) -> Invite | None:
        return next((i for i in self.invites.values() if i.id == invite_id), None)

    async def consume(self, invite: Invite) -> bool:
        self.invites[invite.code_hash] = invite
        return True


class FakeDeviceRepository:
    def __init__(self):
        self.devices: dict[UUID, Device] = {}

    async def add(self, device: Device) -> None:
        self.devices[device.id] = device

    async def get(self, device_id: UUID) -> Device:
        return self.devices[device_id]

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


async def _invite(service: EnrollmentService, *, account_id: UUID, code_hash: str) -> Invite:
    return await service.create_invite(
        account_id=account_id, code_hash=code_hash, roster_json='[{"device_id": "root"}]'
    )


async def test_invite_then_join_admits_device_and_returns_roster():
    uow = FakeUnitOfWork()
    service = EnrollmentService(uow)
    account_id = uuid4()

    invite = await _invite(service, account_id=account_id, code_hash="h1")

    device, roster_json = await service.join(
        code_hash="h1",
        device_name="phone",
        public_key="age1new",
        sign_public_key="sign-new",
        join_mac="mac-1",
    )
    assert device.account_id == account_id
    assert device.is_active is True
    assert device.sign_public_key == "sign-new"
    assert roster_json == '[{"device_id": "root"}]'  # relayed back to the joiner
    # The invite is consumed and the join proof recorded.
    stored = uow.invites.invites[invite.code_hash]
    assert stored.consumed_at is not None
    assert stored.join_mac == "mac-1"
    assert stored.joined_device_id == device.id


async def test_join_with_bad_code_rejected():
    uow = FakeUnitOfWork()
    service = EnrollmentService(uow)
    with pytest.raises(InvalidInvite):
        await service.join(
            code_hash="nope", device_name="x", public_key="age1x", sign_public_key="", join_mac=""
        )


async def test_join_with_consumed_code_rejected():
    uow = FakeUnitOfWork()
    service = EnrollmentService(uow)
    await _invite(service, account_id=uuid4(), code_hash="h1")

    await service.join(
        code_hash="h1", device_name="first", public_key="age1a", sign_public_key="", join_mac=""
    )
    with pytest.raises(InvalidInvite):
        await service.join(
            code_hash="h1",
            device_name="second",
            public_key="age1b",
            sign_public_key="",
            join_mac="",
        )


async def test_join_with_expired_code_rejected():
    uow = FakeUnitOfWork()
    expired = Invite(
        id=uuid4(),
        account_id=uuid4(),
        code_hash="expired",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    uow.invites.invites[expired.code_hash] = expired

    service = EnrollmentService(uow)
    with pytest.raises(InvalidInvite):
        await service.join(
            code_hash="expired",
            device_name="x",
            public_key="age1x",
            sign_public_key="",
            join_mac="",
        )


async def test_join_duplicate_public_key_rejected():
    uow = FakeUnitOfWork()
    service = EnrollmentService(uow)
    await _invite(service, account_id=uuid4(), code_hash="h1")
    await service.join(
        code_hash="h1", device_name="a", public_key="age1dup", sign_public_key="", join_mac=""
    )

    await _invite(service, account_id=uuid4(), code_hash="h2")
    with pytest.raises(DeviceAlreadyExists):
        await service.join(
            code_hash="h2", device_name="b", public_key="age1dup", sign_public_key="", join_mac=""
        )


async def test_join_proof_returns_device_and_mac():
    uow = FakeUnitOfWork()
    service = EnrollmentService(uow)
    account_id = uuid4()
    invite = await _invite(service, account_id=account_id, code_hash="h1")

    # Before consumption: not consumed, no device.
    pending, device = await service.join_proof(account_id=account_id, invite_id=invite.id)
    assert pending.consumed_at is None
    assert device is None

    joined, _ = await service.join(
        code_hash="h1",
        device_name="phone",
        public_key="age1new",
        sign_public_key="sign-new",
        join_mac="mac-1",
    )
    proof, proof_device = await service.join_proof(account_id=account_id, invite_id=invite.id)
    assert proof.join_mac == "mac-1"
    assert proof_device is not None
    assert proof_device.id == joined.id


async def test_join_proof_rejects_other_account():
    uow = FakeUnitOfWork()
    service = EnrollmentService(uow)
    invite = await _invite(service, account_id=uuid4(), code_hash="h1")

    with pytest.raises(InviteNotFound):
        await service.join_proof(account_id=uuid4(), invite_id=invite.id)
