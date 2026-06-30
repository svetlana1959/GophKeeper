"""Unit tests for the device challenge/response auth, exercised against real
age keys (the server encrypts, the test decrypts as the device would)."""

from uuid import UUID, uuid4

import pytest
from pyrage import decrypt, x25519

from gophkeeper.domain.account import Account
from gophkeeper.domain.device import ACTIVE, REVOKED, Device
from gophkeeper.domain.errors import AuthenticationError, DeviceNotFound
from gophkeeper.services.auth_service import AuthService


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

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def commit(self):
        pass

    async def rollback(self):
        pass


def _device(uow: FakeUnitOfWork, *, status: str = ACTIVE) -> tuple[Device, x25519.Identity]:
    identity = x25519.Identity.generate()
    public_key = str(identity.to_public())
    device = Device(
        id=uuid4(),
        account_id=uuid4(),
        device_name="laptop",
        public_key=public_key,
        status=status,
    )
    uow.devices.devices[device.id] = device
    return device, identity


async def test_challenge_verify_issues_usable_session():
    uow = FakeUnitOfWork()
    device, identity = _device(uow)
    service = AuthService(uow)

    ciphertext, challenge_token = await service.challenge(public_key=device.public_key)

    # The device decrypts the challenge with its private key.
    nonce = decrypt(ciphertext, [identity])
    access_token, expires_in = await service.verify(
        challenge_token=challenge_token, nonce=nonce
    )
    assert expires_in > 0
    assert device.last_seen_at is not None  # verify recorded the login

    principal = service.principal(access_token)
    assert principal.device_id == device.id
    assert principal.account_id == device.account_id


async def test_challenge_unknown_device_rejected():
    uow = FakeUnitOfWork()
    service = AuthService(uow)
    with pytest.raises(AuthenticationError):
        await service.challenge(public_key="age1nope")


async def test_challenge_revoked_device_rejected():
    uow = FakeUnitOfWork()
    device, _ = _device(uow, status=REVOKED)
    service = AuthService(uow)
    with pytest.raises(AuthenticationError):
        await service.challenge(public_key=device.public_key)


async def test_verify_wrong_nonce_rejected():
    uow = FakeUnitOfWork()
    device, _ = _device(uow)
    service = AuthService(uow)
    _, challenge_token = await service.challenge(public_key=device.public_key)
    with pytest.raises(AuthenticationError):
        await service.verify(challenge_token=challenge_token, nonce=b"wrong-nonce")


async def test_session_token_rejected_as_challenge_and_vice_versa():
    uow = FakeUnitOfWork()
    device, identity = _device(uow)
    service = AuthService(uow)

    ciphertext, challenge_token = await service.challenge(public_key=device.public_key)
    nonce = decrypt(ciphertext, [identity])
    access_token, _ = await service.verify(challenge_token=challenge_token, nonce=nonce)

    # A session token is not a valid challenge answer...
    with pytest.raises(AuthenticationError):
        await service.verify(challenge_token=access_token, nonce=nonce)
    # ...and a challenge token is not a session bearer.
    with pytest.raises(AuthenticationError):
        service.principal(challenge_token)
