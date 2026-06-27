"""Unit tests for SecretService's multi-device access control (issue #69).

REVISION per review: share()/revoke() are gone from SecretService — direct
device-to-device grants bypassed the re-encryption step a Zero-Knowledge
system requires. The replacement handshake-broker flow (request/list/approve/
reject) is tested in test_access_request_service.py. The tests here cover
what's left in SecretService: store/fetch/update/list_for_device and the
access checks they share.

- test_store_grants_creating_device_access      -> "trusted devices ... can use"
- test_access_maintained_after_update            -> "access maintained after synchronization"
- test_fetch_denied_for_untrusted_device          -> "not trusted ... access is denied"
- test_fetch_denied_for_deactivated_device        -> "not trusted ... access is denied"
- test_list_for_device_returns_latest_after_reconnect -> "connection restored ... latest data"
"""

from uuid import UUID, uuid4

import pytest

from gophkeeper.domain.device import Device
from gophkeeper.domain.errors import AccessDenied, DeviceNotFound, SecretNotFound
from gophkeeper.domain.secret import Secret
from gophkeeper.services.secret_service import SecretService


class FakeDeviceRepository:
    def __init__(self):
        self.devices: dict[UUID, Device] = {}

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


class FakeSecretRepository:
    def __init__(self):
        self.secrets: dict[UUID, Secret] = {}

    async def add(self, secret: Secret) -> None:
        self.secrets[secret.id] = secret

    async def get(self, secret_id: UUID) -> Secret:
        if secret_id not in self.secrets:
            raise SecretNotFound(secret_id)
        return self.secrets[secret_id]

    async def list_for_account(self, account_id: str, *, include_deleted: bool = False):
        return [s for s in self.secrets.values() if s.account_id == account_id]

    async def save(self, secret: Secret) -> None:
        self.secrets[secret.id] = secret


class FakeSecretAccessRepository:
    def __init__(self):
        self.grants: set[tuple[UUID, UUID]] = set()

    async def grant(self, secret_id: UUID, device_id: UUID) -> None:
        self.grants.add((secret_id, device_id))

    async def revoke(self, secret_id: UUID, device_id: UUID) -> None:
        self.grants.discard((secret_id, device_id))

    async def has_access(self, secret_id: UUID, device_id: UUID) -> bool:
        return (secret_id, device_id) in self.grants

    async def list_secret_ids_for_device(self, device_id: UUID) -> list[UUID]:
        return [sid for sid, did in self.grants if did == device_id]

    async def list_device_ids_for_secret(self, secret_id: UUID) -> list[UUID]:
        return [did for sid, did in self.grants if sid == secret_id]


class FakeUnitOfWork:
    def __init__(self):
        self.devices = FakeDeviceRepository()
        self.secrets = FakeSecretRepository()
        self.access = FakeSecretAccessRepository()
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def commit(self):
        self.committed = True

    async def rollback(self):
        pass


def _device(*, is_active: bool = True) -> Device:
    return Device(id=uuid4(), device_name="d", public_key="pk", is_active=is_active)


async def test_store_grants_creating_device_access():
    uow = FakeUnitOfWork()
    device = _device()
    await uow.devices.add(device)
    service = SecretService(uow)
    secret_id = uuid4()

    await service.store(
        account_id="acc", secret_id=secret_id, device_id=device.id, ciphertext=b"v1"
    )

    fetched = await service.fetch(secret_id, device_id=device.id)
    assert fetched.id == secret_id


async def test_access_maintained_after_update():
    uow = FakeUnitOfWork()
    device = _device()
    await uow.devices.add(device)
    service = SecretService(uow)
    secret_id = uuid4()

    await service.store(
        account_id="acc", secret_id=secret_id, device_id=device.id, ciphertext=b"v1"
    )
    await service.update(
        secret_id=secret_id, device_id=device.id, ciphertext=b"v2", base_version=1
    )

    fetched = await service.fetch(secret_id, device_id=device.id)
    assert fetched.ciphertext == b"v2"
    assert fetched.version == 2


async def test_fetch_denied_for_untrusted_device():
    uow = FakeUnitOfWork()
    owner = _device()
    stranger = _device()
    await uow.devices.add(owner)
    await uow.devices.add(stranger)
    service = SecretService(uow)
    secret_id = uuid4()

    await service.store(
        account_id="acc", secret_id=secret_id, device_id=owner.id, ciphertext=b"v1"
    )

    with pytest.raises(AccessDenied):
        await service.fetch(secret_id, device_id=stranger.id)


async def test_fetch_denied_for_deactivated_device():
    """A revoked device loses access immediately, even with an existing grant."""
    uow = FakeUnitOfWork()
    device = _device()
    await uow.devices.add(device)
    service = SecretService(uow)
    secret_id = uuid4()

    await service.store(
        account_id="acc", secret_id=secret_id, device_id=device.id, ciphertext=b"v1"
    )

    device.deactivate()
    await uow.devices.save(device)

    with pytest.raises(AccessDenied):
        await service.fetch(secret_id, device_id=device.id)


async def test_list_for_device_returns_latest_after_reconnect():
    """A trusted device reconnecting sees the latest version of everything it
    has access to, regardless of which device wrote it most recently."""
    uow = FakeUnitOfWork()
    device_a = _device()
    await uow.devices.add(device_a)
    service = SecretService(uow)

    secret_id = uuid4()
    await service.store(
        account_id="acc", secret_id=secret_id, device_id=device_a.id, ciphertext=b"v1"
    )
    await service.update(
        secret_id=secret_id, device_id=device_a.id, ciphertext=b"v2", base_version=1
    )

    synced = await service.list_for_device(device_a.id)
    assert len(synced) == 1
    assert synced[0].ciphertext == b"v2"
    assert synced[0].version == 2
