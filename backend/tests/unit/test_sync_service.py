"""Unit tests for SyncService (issue #68 — multi-device synchronization).

Each test maps to one acceptance criterion:

- test_syncs_between_multiple_devices              -> criterion 1
- test_synced_data_is_latest_version                -> criterion 2
- test_sync_report_carries_overall_status            -> criterion 3
- test_access_revoked_reported_as_explicit_failure   -> criterion 4
- test_change_on_one_device_visible_on_sync_for_other -> criterion 5

Plus edge cases found during review: mixed-outcome batches, an entirely
untrusted caller (total failure, not embedded in the report), and a
deactivated device.
"""

from uuid import UUID, uuid4

import pytest

from gophkeeper.domain.device import Device
from gophkeeper.domain.errors import AccessDenied, DeviceNotFound, SecretNotFound
from gophkeeper.domain.secret import Secret
from gophkeeper.domain.sync import ClientSecretState, SyncOutcome, SyncStatus
from gophkeeper.services.sync_service import SyncService


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


async def test_syncs_between_multiple_devices():
    """Criterion 1: with more than one trusted device, both can sync."""
    uow = FakeUnitOfWork()
    device_a = _device()
    device_b = _device()
    await uow.devices.add(device_a)
    await uow.devices.add(device_b)
    secret_id = uuid4()
    secret = Secret(id=secret_id, account_id="acc", ciphertext=b"v1")
    await uow.secrets.add(secret)
    await uow.access.grant(secret_id, device_a.id)
    await uow.access.grant(secret_id, device_b.id)

    service = SyncService(uow)

    report_a = await service.sync(device_id=device_a.id, client_state=[])
    report_b = await service.sync(device_id=device_b.id, client_state=[])

    assert report_a.status == SyncStatus.OK
    assert report_b.status == SyncStatus.OK
    assert report_a.results[0].secret_id == secret_id
    assert report_b.results[0].secret_id == secret_id


async def test_synced_data_is_latest_version():
    """Criterion 2: after sync, the most current version is what's returned."""
    uow = FakeUnitOfWork()
    device = _device()
    await uow.devices.add(device)
    secret_id = uuid4()
    secret = Secret(id=secret_id, account_id="acc", ciphertext=b"v1")
    secret.update(b"v2", base_version=1)
    secret.update(b"v3", base_version=2)
    await uow.secrets.add(secret)
    await uow.access.grant(secret_id, device.id)

    service = SyncService(uow)
    report = await service.sync(
        device_id=device.id, client_state=[ClientSecretState(id=secret_id, version=1)]
    )

    assert report.results[0].outcome == SyncOutcome.UPDATED
    assert report.results[0].version == 3
    assert report.results[0].ciphertext == b"v3"


async def test_sync_report_carries_overall_status():
    """Criterion 3: the caller receives a sync status, not just raw data."""
    uow = FakeUnitOfWork()
    device = _device()
    await uow.devices.add(device)
    secret_id = uuid4()
    await uow.secrets.add(Secret(id=secret_id, account_id="acc", ciphertext=b"v1"))
    await uow.access.grant(secret_id, device.id)

    service = SyncService(uow)
    report = await service.sync(
        device_id=device.id, client_state=[ClientSecretState(id=secret_id, version=1)]
    )

    assert report.status == SyncStatus.OK
    assert report.has_failures is False


async def test_access_revoked_reported_as_explicit_failure():
    """Criterion 4: a sync failure for one item is surfaced explicitly, not
    silently dropped, and the overall status reflects it."""
    uow = FakeUnitOfWork()
    device = _device()
    await uow.devices.add(device)
    # the device asks about a secret it was never granted access to
    phantom_secret_id = uuid4()

    service = SyncService(uow)
    report = await service.sync(
        device_id=device.id,
        client_state=[ClientSecretState(id=phantom_secret_id, version=1)],
    )

    assert report.status == SyncStatus.PARTIAL
    assert report.has_failures is True
    assert report.results[0].outcome == SyncOutcome.ACCESS_REVOKED
    # no ciphertext should ever be disclosed for a denied item
    assert report.results[0].ciphertext is None
    assert report.results[0].version is None


async def test_change_on_one_device_visible_on_sync_for_other():
    """Criterion 5: device A changes data, device B's next sync sees it."""
    uow = FakeUnitOfWork()
    device_a = _device()
    device_b = _device()
    await uow.devices.add(device_a)
    await uow.devices.add(device_b)
    secret_id = uuid4()
    secret = Secret(id=secret_id, account_id="acc", ciphertext=b"v1")
    await uow.secrets.add(secret)
    await uow.access.grant(secret_id, device_a.id)
    await uow.access.grant(secret_id, device_b.id)

    service = SyncService(uow)

    # both devices start in sync at version 1
    await service.sync(
        device_id=device_b.id, client_state=[ClientSecretState(id=secret_id, version=1)]
    )

    # device A changes the secret
    secret.update(b"v2-from-A", base_version=1)
    await uow.secrets.save(secret)

    # device B syncs again with its now-stale version=1
    report = await service.sync(
        device_id=device_b.id, client_state=[ClientSecretState(id=secret_id, version=1)]
    )

    assert report.results[0].outcome == SyncOutcome.UPDATED
    assert report.results[0].ciphertext == b"v2-from-A"
    assert report.results[0].version == 2


async def test_mixed_batch_reports_every_outcome_independently():
    """A single sync call can contain UPDATED, UP_TO_DATE, NEW, and
    ACCESS_REVOKED items simultaneously, each reported on its own."""
    uow = FakeUnitOfWork()
    device = _device()
    await uow.devices.add(device)

    fresh_id, stale_id, new_id, phantom_id = uuid4(), uuid4(), uuid4(), uuid4()

    fresh = Secret(id=fresh_id, account_id="acc", ciphertext=b"f")
    stale = Secret(id=stale_id, account_id="acc", ciphertext=b"s1")
    stale.update(b"s2", base_version=1)
    new = Secret(id=new_id, account_id="acc", ciphertext=b"n")

    for s in (fresh, stale, new):
        await uow.secrets.add(s)
        await uow.access.grant(s.id, device.id)

    service = SyncService(uow)
    report = await service.sync(
        device_id=device.id,
        client_state=[
            ClientSecretState(id=fresh_id, version=1),
            ClientSecretState(id=stale_id, version=1),
            ClientSecretState(id=phantom_id, version=1),
        ],
    )

    by_id = {r.secret_id: r for r in report.results}
    assert report.status == SyncStatus.PARTIAL
    assert by_id[fresh_id].outcome == SyncOutcome.UP_TO_DATE
    assert by_id[stale_id].outcome == SyncOutcome.UPDATED
    assert by_id[stale_id].version == 2
    assert by_id[phantom_id].outcome == SyncOutcome.ACCESS_REVOKED
    assert by_id[new_id].outcome == SyncOutcome.NEW


async def test_untrusted_device_raises_instead_of_partial_report():
    """An entirely unknown calling device is a total failure (raises), not a
    PARTIAL report — that distinction matters at the HTTP layer (403/404
    instead of 200 with an empty/odd body)."""
    uow = FakeUnitOfWork()
    service = SyncService(uow)

    with pytest.raises(DeviceNotFound):
        await service.sync(device_id=uuid4(), client_state=[])


async def test_deactivated_device_cannot_sync():
    uow = FakeUnitOfWork()
    device = _device()
    await uow.devices.add(device)
    device.deactivate()
    await uow.devices.save(device)

    service = SyncService(uow)

    with pytest.raises(AccessDenied):
        await service.sync(device_id=device.id, client_state=[])


async def test_empty_client_state_and_no_secrets_returns_ok_empty():
    uow = FakeUnitOfWork()
    device = _device()
    await uow.devices.add(device)

    service = SyncService(uow)
    report = await service.sync(device_id=device.id, client_state=[])

    assert report.status == SyncStatus.OK
    assert report.results == []
