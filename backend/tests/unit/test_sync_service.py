import dataclasses
from uuid import UUID, uuid4

from gophkeeper.domain.device import Device
from gophkeeper.domain.errors import SecretNotFound, VersionConflict
from gophkeeper.domain.secret import Secret
from gophkeeper.services.sync_service import PushItem, SyncService

_ACCOUNT_ID = uuid4()
_ACCOUNT = str(_ACCOUNT_ID)
_DEVICE = uuid4()  # the pushing/pulling device


class FakeSecretRepository:
    def __init__(self):
        self.secrets: dict[UUID, Secret] = {}
        self.recipients: dict[UUID, set[UUID]] = {}
        self._seq = 0

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    async def get(self, secret_id: UUID) -> Secret:
        if secret_id not in self.secrets:
            raise SecretNotFound(secret_id)
        # Return a working copy so the stored "row" only changes on save() —
        # this is what lets compare-and-set see the committed version.
        return dataclasses.replace(self.secrets[secret_id])

    async def add(self, secret: Secret) -> None:
        secret.seq = self._next_seq()
        self.secrets[secret.id] = secret

    async def save(self, secret: Secret, *, expected_version: int | None = None) -> None:
        if expected_version is not None:
            stored = self.secrets.get(secret.id)
            actual = stored.version if stored else 0
            if actual != expected_version:
                raise VersionConflict(secret.id, expected=expected_version, actual=actual)
        secret.seq = self._next_seq()
        self.secrets[secret.id] = secret

    async def set_recipients(self, secret_id: UUID, device_ids: list[UUID]) -> None:
        self.recipients[secret_id] = set(device_ids)

    async def list_changed_since(
        self, account_id: str, device_id: UUID, since_seq: int, *, limit: int
    ) -> list[Secret]:
        rows = [
            s
            for s in self.secrets.values()
            if s.account_id == account_id
            and s.seq > since_seq
            and device_id in self.recipients.get(s.id, set())
        ]
        return sorted(rows, key=lambda s: s.seq)[:limit]


class FakeDeviceRepository:
    def __init__(self):
        self.devices: dict[UUID, Device] = {}

    def add_sync(self, device: Device) -> None:
        self.devices[device.id] = device

    async def find_by_public_key(self, public_key: str) -> Device | None:
        return next((d for d in self.devices.values() if d.public_key == public_key), None)


class FakeUnitOfWork:
    def __init__(self):
        self.secrets = FakeSecretRepository()
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


async def test_push_creates_then_pull_returns_it():
    uow = FakeUnitOfWork()
    service = SyncService(uow)
    sid = uuid4()

    results = await service.push(
        account_id=_ACCOUNT, device_id=_DEVICE, items=[PushItem(id=sid, ciphertext=b"ct-1")]
    )
    assert results[0].status == "applied"
    assert results[0].version == 1
    assert uow.committed is True

    secrets, cursor = await service.changes(account_id=_ACCOUNT, device_id=_DEVICE, since=0)
    assert [s.id for s in secrets] == [sid]
    assert cursor == results[0].seq


async def test_pull_since_cursor_returns_only_newer():
    uow = FakeUnitOfWork()
    service = SyncService(uow)

    a = uuid4()
    await service.push(
        account_id=_ACCOUNT, device_id=_DEVICE, items=[PushItem(id=a, ciphertext=b"a")]
    )
    _, cursor = await service.changes(account_id=_ACCOUNT, device_id=_DEVICE, since=0)

    b = uuid4()
    await service.push(
        account_id=_ACCOUNT, device_id=_DEVICE, items=[PushItem(id=b, ciphertext=b"b")]
    )

    secrets, new_cursor = await service.changes(
        account_id=_ACCOUNT, device_id=_DEVICE, since=cursor
    )
    assert [s.id for s in secrets] == [b]
    assert new_cursor > cursor


async def test_push_update_bumps_version():
    uow = FakeUnitOfWork()
    service = SyncService(uow)
    sid = uuid4()

    await service.push(
        account_id=_ACCOUNT, device_id=_DEVICE, items=[PushItem(id=sid, ciphertext=b"v1")]
    )
    results = await service.push(
        account_id=_ACCOUNT,
        device_id=_DEVICE,
        items=[PushItem(id=sid, ciphertext=b"v2", base_version=1)],
    )
    assert results[0].status == "applied"
    assert results[0].version == 2


async def test_push_stale_update_is_conflict_not_fatal():
    uow = FakeUnitOfWork()
    service = SyncService(uow)
    sid = uuid4()
    other = uuid4()

    await service.push(
        account_id=_ACCOUNT, device_id=_DEVICE, items=[PushItem(id=sid, ciphertext=b"v1")]
    )
    results = await service.push(
        account_id=_ACCOUNT,
        device_id=_DEVICE,
        items=[
            PushItem(id=sid, ciphertext=b"stale", base_version=0),
            PushItem(id=other, ciphertext=b"fresh"),
        ],
    )
    by_id = {r.id: r for r in results}
    assert by_id[sid].status == "conflict"
    assert by_id[sid].version == 1
    assert by_id[other].status == "applied"


async def test_push_delete_tombstones():
    uow = FakeUnitOfWork()
    service = SyncService(uow)
    sid = uuid4()

    await service.push(
        account_id=_ACCOUNT, device_id=_DEVICE, items=[PushItem(id=sid, ciphertext=b"v1")]
    )
    results = await service.push(
        account_id=_ACCOUNT,
        device_id=_DEVICE,
        items=[PushItem(id=sid, ciphertext=b"", deleted=True)],
    )
    assert results[0].status == "applied"

    secrets, _ = await service.changes(account_id=_ACCOUNT, device_id=_DEVICE, since=0)
    assert secrets[0].deleted is True


async def test_push_to_foreign_secret_is_conflict():
    uow = FakeUnitOfWork()
    service = SyncService(uow)
    sid = uuid4()

    await service.push(
        account_id=str(uuid4()), device_id=uuid4(), items=[PushItem(id=sid, ciphertext=b"theirs")]
    )
    results = await service.push(
        account_id=_ACCOUNT,
        device_id=_DEVICE,
        items=[PushItem(id=sid, ciphertext=b"mine", base_version=1)],
    )
    assert results[0].status == "conflict"
    secrets, _ = await service.changes(account_id=_ACCOUNT, device_id=_DEVICE, since=0)
    assert secrets == []


async def test_update_with_empty_recipients_preserves_sharing():
    uow = FakeUnitOfWork()
    dev_a = Device(id=uuid4(), account_id=_ACCOUNT_ID, device_name="a", public_key="age1a")
    dev_b = Device(id=uuid4(), account_id=_ACCOUNT_ID, device_name="b", public_key="age1b")
    uow.devices.add_sync(dev_a)
    uow.devices.add_sync(dev_b)
    service = SyncService(uow)
    sid = uuid4()

    # A shares a secret with B, then edits it without re-sending recipients.
    await service.push(
        account_id=_ACCOUNT,
        device_id=dev_a.id,
        items=[PushItem(id=sid, ciphertext=b"v1", recipients=["age1a", "age1b"])],
    )
    await service.push(
        account_id=_ACCOUNT,
        device_id=dev_a.id,
        items=[PushItem(id=sid, ciphertext=b"v2", base_version=1)],  # no recipients
    )

    b_secrets, _ = await service.changes(account_id=_ACCOUNT, device_id=dev_b.id, since=0)
    assert {s.id for s in b_secrets} == {sid}  # B still sees it; edit didn't revoke B


async def test_delete_of_unknown_secret_is_noop_not_error():
    uow = FakeUnitOfWork()
    service = SyncService(uow)
    results = await service.push(
        account_id=_ACCOUNT,
        device_id=_DEVICE,
        items=[PushItem(id=uuid4(), ciphertext=b"", deleted=True)],
    )
    assert results[0].status == "applied"


async def test_pull_is_scoped_to_recipients():
    uow = FakeUnitOfWork()
    dev_a = Device(id=uuid4(), account_id=_ACCOUNT_ID, device_name="a", public_key="age1a")
    dev_b = Device(id=uuid4(), account_id=_ACCOUNT_ID, device_name="b", public_key="age1b")
    uow.devices.add_sync(dev_a)
    uow.devices.add_sync(dev_b)
    service = SyncService(uow)

    shared = uuid4()
    private_to_a = uuid4()
    # A pushes one secret to both, one only to itself.
    await service.push(
        account_id=_ACCOUNT,
        device_id=dev_a.id,
        items=[
            PushItem(id=shared, ciphertext=b"s", recipients=["age1a", "age1b"]),
            PushItem(id=private_to_a, ciphertext=b"p", recipients=["age1a"]),
        ],
    )

    a_secrets, _ = await service.changes(account_id=_ACCOUNT, device_id=dev_a.id, since=0)
    b_secrets, _ = await service.changes(account_id=_ACCOUNT, device_id=dev_b.id, since=0)

    assert {s.id for s in a_secrets} == {shared, private_to_a}
    assert {s.id for s in b_secrets} == {shared}  # B never sees A's private secret
