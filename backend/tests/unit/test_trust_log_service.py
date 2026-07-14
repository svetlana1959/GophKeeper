from uuid import UUID, uuid4

import pytest

from gophkeeper.domain.errors import TrustCertConflict
from gophkeeper.domain.trust import TrustCert
from gophkeeper.services.trust_log_service import TrustLogService


class FakeTrustCertRepository:
    def __init__(self) -> None:
        self.certs: list[TrustCert] = []
        self._log_seq = 0

    async def add(self, cert: TrustCert) -> int:
        self._log_seq += 1
        cert.log_seq = self._log_seq
        self.certs.append(cert)
        return cert.log_seq

    async def max_issuer_seq(self, issuer_device_id: UUID) -> int | None:
        seqs = [c.issuer_seq for c in self.certs if c.issuer_device_id == issuer_device_id]
        return max(seqs) if seqs else None

    async def list_since(self, account_id: UUID, since: int, *, limit: int) -> list[TrustCert]:
        return [
            c
            for c in sorted(self.certs, key=lambda c: c.log_seq)
            if c.account_id == account_id and c.log_seq > since
        ][:limit]


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.trust_certs = FakeTrustCertRepository()
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def commit(self):
        self.committed = True

    async def rollback(self):
        pass


def _payload(kind: str, issuer: UUID, seq: int) -> dict:
    return {"kind": kind, "issuer_id": str(issuer), "seq": seq, "sig": "s"}


async def test_publish_assigns_log_seq_and_commits():
    uow = FakeUnitOfWork()
    service = TrustLogService(uow)
    account, issuer = uuid4(), uuid4()

    cert = await service.publish(
        account_id=account,
        issuer_device_id=issuer,
        kind="vouch",
        issuer_seq=0,
        payload=_payload("vouch", issuer, 0),
    )

    assert cert.log_seq == 1
    assert uow.committed


async def test_publish_requires_contiguous_seq():
    uow = FakeUnitOfWork()
    service = TrustLogService(uow)
    account, issuer = uuid4(), uuid4()

    await service.publish(
        account_id=account,
        issuer_device_id=issuer,
        kind="vouch",
        issuer_seq=0,
        payload=_payload("vouch", issuer, 0),
    )

    # Skipping seq 1 for seq 2 is a gap.
    with pytest.raises(TrustCertConflict):
        await service.publish(
            account_id=account,
            issuer_device_id=issuer,
            kind="revoke",
            issuer_seq=2,
            payload=_payload("revoke", issuer, 2),
        )

    # Re-publishing seq 0 is a duplicate/rewind.
    with pytest.raises(TrustCertConflict):
        await service.publish(
            account_id=account,
            issuer_device_id=issuer,
            kind="vouch",
            issuer_seq=0,
            payload=_payload("vouch", issuer, 0),
        )


async def test_each_issuer_has_its_own_seq_space():
    uow = FakeUnitOfWork()
    service = TrustLogService(uow)
    account, issuer_a, issuer_b = uuid4(), uuid4(), uuid4()

    # Both issuers independently start at seq 0.
    await service.publish(
        account_id=account,
        issuer_device_id=issuer_a,
        kind="vouch",
        issuer_seq=0,
        payload=_payload("vouch", issuer_a, 0),
    )
    await service.publish(
        account_id=account,
        issuer_device_id=issuer_b,
        kind="vouch",
        issuer_seq=0,
        payload=_payload("vouch", issuer_b, 0),
    )

    assert len(uow.trust_certs.certs) == 2


async def test_changes_returns_since_cursor():
    uow = FakeUnitOfWork()
    service = TrustLogService(uow)
    account, issuer = uuid4(), uuid4()
    for seq in range(3):
        await service.publish(
            account_id=account,
            issuer_device_id=issuer,
            kind="vouch",
            issuer_seq=seq,
            payload=_payload("vouch", issuer, seq),
        )

    certs, cursor = await service.changes(account_id=account, since=0)
    assert [c.issuer_seq for c in certs] == [0, 1, 2]
    assert cursor == 3

    tail, tail_cursor = await service.changes(account_id=account, since=2)
    assert [c.issuer_seq for c in tail] == [2]
    assert tail_cursor == 3

    # A cursor past the end yields nothing and holds steady.
    none, held = await service.changes(account_id=account, since=3)
    assert none == []
    assert held == 3


async def test_changes_scoped_to_account():
    uow = FakeUnitOfWork()
    service = TrustLogService(uow)
    mine, other, issuer = uuid4(), uuid4(), uuid4()
    await service.publish(
        account_id=other,
        issuer_device_id=issuer,
        kind="vouch",
        issuer_seq=0,
        payload=_payload("vouch", issuer, 0),
    )

    certs, _ = await service.changes(account_id=mine, since=0)
    assert certs == []
