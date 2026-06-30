from uuid import UUID, uuid4

from gophkeeper.domain.errors import SecretNotFound
from gophkeeper.domain.secret import Secret
from gophkeeper.services.sync_service import PushItem, SyncService

_ACCOUNT = "acc-1"


class FakeSecretRepository:
    def __init__(self):
        self.secrets: dict[UUID, Secret] = {}
        self._seq = 0

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    async def get(self, secret_id: UUID) -> Secret:
        if secret_id not in self.secrets:
            raise SecretNotFound(secret_id)
        return self.secrets[secret_id]

    async def add(self, secret: Secret) -> None:
        secret.seq = self._next_seq()
        self.secrets[secret.id] = secret

    async def save(self, secret: Secret) -> None:
        secret.seq = self._next_seq()
        self.secrets[secret.id] = secret

    async def list_changed_since(
        self, account_id: str, since_seq: int, *, limit: int
    ) -> list[Secret]:
        rows = [
            s
            for s in self.secrets.values()
            if s.account_id == account_id and s.seq > since_seq
        ]
        return sorted(rows, key=lambda s: s.seq)[:limit]


class FakeUnitOfWork:
    def __init__(self):
        self.secrets = FakeSecretRepository()
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
        account_id=_ACCOUNT,
        items=[PushItem(id=sid, ciphertext=b"ct-1")],
    )
    assert results[0].status == "applied"
    assert results[0].version == 1
    assert uow.committed is True

    secrets, cursor = await service.changes(account_id=_ACCOUNT, since=0)
    assert [s.id for s in secrets] == [sid]
    assert cursor == results[0].seq


async def test_pull_since_cursor_returns_only_newer():
    uow = FakeUnitOfWork()
    service = SyncService(uow)

    a = uuid4()
    await service.push(account_id=_ACCOUNT, items=[PushItem(id=a, ciphertext=b"a")])
    _, cursor = await service.changes(account_id=_ACCOUNT, since=0)

    b = uuid4()
    await service.push(account_id=_ACCOUNT, items=[PushItem(id=b, ciphertext=b"b")])

    secrets, new_cursor = await service.changes(account_id=_ACCOUNT, since=cursor)
    assert [s.id for s in secrets] == [b]
    assert new_cursor > cursor


async def test_push_update_bumps_version():
    uow = FakeUnitOfWork()
    service = SyncService(uow)
    sid = uuid4()

    await service.push(account_id=_ACCOUNT, items=[PushItem(id=sid, ciphertext=b"v1")])
    results = await service.push(
        account_id=_ACCOUNT,
        items=[PushItem(id=sid, ciphertext=b"v2", base_version=1)],
    )
    assert results[0].status == "applied"
    assert results[0].version == 2


async def test_push_stale_update_is_conflict_not_fatal():
    uow = FakeUnitOfWork()
    service = SyncService(uow)
    sid = uuid4()
    other = uuid4()

    await service.push(account_id=_ACCOUNT, items=[PushItem(id=sid, ciphertext=b"v1")])
    # current version is 1; pushing against base_version 0 is stale.
    results = await service.push(
        account_id=_ACCOUNT,
        items=[
            PushItem(id=sid, ciphertext=b"stale", base_version=0),
            PushItem(id=other, ciphertext=b"fresh"),
        ],
    )
    by_id = {r.id: r for r in results}
    assert by_id[sid].status == "conflict"
    assert by_id[sid].version == 1  # the winning version, for the client to reconcile
    assert by_id[other].status == "applied"  # rest of the batch still applied


async def test_push_delete_tombstones():
    uow = FakeUnitOfWork()
    service = SyncService(uow)
    sid = uuid4()

    await service.push(account_id=_ACCOUNT, items=[PushItem(id=sid, ciphertext=b"v1")])
    results = await service.push(
        account_id=_ACCOUNT,
        items=[PushItem(id=sid, ciphertext=b"", deleted=True)],
    )
    assert results[0].status == "applied"

    secrets, _ = await service.changes(account_id=_ACCOUNT, since=0)
    assert secrets[0].deleted is True


async def test_push_to_foreign_secret_is_conflict():
    uow = FakeUnitOfWork()
    service = SyncService(uow)
    sid = uuid4()

    await service.push(account_id="other-acc", items=[PushItem(id=sid, ciphertext=b"theirs")])
    results = await service.push(
        account_id=_ACCOUNT,
        items=[PushItem(id=sid, ciphertext=b"mine", base_version=1)],
    )
    assert results[0].status == "conflict"
    # The foreign secret is untouched and never surfaces to this account.
    secrets, _ = await service.changes(account_id=_ACCOUNT, since=0)
    assert secrets == []
