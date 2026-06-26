"""Unit tests for SecretService's multi-device access control (issue #69).

Each test below maps to one acceptance criterion from the issue:

- test_store_grants_creating_device_access            -> "trusted devices ... can use"
- test_second_trusted_device_can_fetch_after_share     -> "data available on each trusted device"
- test_access_maintained_after_update                  -> "access maintained after synchronization"
- test_fetch_denied_for_untrusted_device                -> "not trusted ... access is denied"
- test_list_for_device_returns_latest_after_reconnect   -> "connection restored ... latest available data"
"""

import pytest

from gophkeeper.domain.device import Device
from gophkeeper.domain.secret import Secret
from gophkeeper.domain.errors import AccessDenied, DeviceNotFound, SecretNotFound
from gophkeeper.services.secret_service import SecretService
from uuid import UUID, uuid4


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

    # the device that stored it can immediately fetch it back
    fetched = await service.fetch(secret_id, device_id=device.id)
    assert fetched.id == secret_id


async def test_second_trusted_device_can_fetch_after_share():
    uow = FakeUnitOfWork()
    device_a = _device()
    device_b = _device()
    await uow.devices.add(device_a)
    await uow.devices.add(device_b)
    service = SecretService(uow)
    secret_id = uuid4()

    await service.store(
        account_id="acc", secret_id=secret_id, device_id=device_a.id, ciphertext=b"v1"
    )

    # device_b has no access yet
    with pytest.raises(AccessDenied):
        await service.fetch(secret_id, device_id=device_b.id)

    # device_a shares it with device_b
    await service.share(secret_id, from_device_id=device_a.id, to_device_id=device_b.id)

    # now device_b can see it too
    fetched = await service.fetch(secret_id, device_id=device_b.id)
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

    # access persists across the update — the grant is independent of version
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
    """Simulates a trusted device dropping off and reconnecting: it should see
    every secret it has access to, with the latest version, regardless of
    which device wrote the most recent update."""
    uow = FakeUnitOfWork()
    device_a = _device()
    device_b = _device()
    await uow.devices.add(device_a)
    await uow.devices.add(device_b)
    service = SecretService(uow)

    secret_id = uuid4()
    await service.store(
        account_id="acc", secret_id=secret_id, device_id=device_a.id, ciphertext=b"v1"
    )
    await service.share(secret_id, from_device_id=device_a.id, to_device_id=device_b.id)

    # device_b writes an update while device_a is "offline"
    await service.update(
        secret_id=secret_id, device_id=device_b.id, ciphertext=b"v2", base_version=1
    )

    # device_a "reconnects" and syncs
    synced = await service.list_for_device(device_a.id)
    assert len(synced) == 1
    assert synced[0].ciphertext == b"v2"
    assert synced[0].version == 2


async def test_owner_can_revoke_access_of_shared_device():
    uow = FakeUnitOfWork()
    owner = _device()
    other = _device()
    await uow.devices.add(owner)
    await uow.devices.add(other)
    service = SecretService(uow)
    secret_id = uuid4()

    await service.store(account_id="acc", secret_id=secret_id, device_id=owner.id, ciphertext=b"v1")
    await service.share(secret_id, from_device_id=owner.id, to_device_id=other.id)

    # confirm the share worked before revoking it
    fetched = await service.fetch(secret_id, device_id=other.id)
    assert fetched.id == secret_id

    await service.revoke(secret_id, requesting_device_id=owner.id, target_device_id=other.id)

    with pytest.raises(AccessDenied):
        await service.fetch(secret_id, device_id=other.id)


async def test_revoke_denied_for_device_without_access_to_secret():
    uow = FakeUnitOfWork()
    owner = _device()
    other = _device()
    stranger = _device()
    await uow.devices.add(owner)
    await uow.devices.add(other)
    await uow.devices.add(stranger)
    service = SecretService(uow)
    secret_id = uuid4()

    await service.store(account_id="acc", secret_id=secret_id, device_id=owner.id, ciphertext=b"v1")
    await service.share(secret_id, from_device_id=owner.id, to_device_id=other.id)

    # stranger never had access to this secret at all
    with pytest.raises(AccessDenied):
        await service.revoke(secret_id, requesting_device_id=stranger.id, target_device_id=other.id)

    # and other's access must still be intact — the revoke attempt above
    # must not have gone through
    fetched = await service.fetch(secret_id, device_id=other.id)
    assert fetched.id == secret_id
