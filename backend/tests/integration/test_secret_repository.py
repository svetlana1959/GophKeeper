"""Example integration test — exercises the real adapter against PostgreSQL.

Where the unit tests prove the domain rules in isolation, this proves the
infrastructure: that ``SqlAlchemyUnitOfWork`` + ``SqlAlchemySecretRepository``
actually persist and read back through SQL, and that commit/rollback behave.
Skipped unless ``TEST_DATABASE_URL`` is set (see conftest).
"""

from uuid import uuid4

import pytest

from gophkeeper.domain.errors import SecretNotFound
from gophkeeper.domain.secret import Secret
from gophkeeper.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


async def test_store_and_fetch_round_trip(database):
    secret_id = uuid4()
    async with SqlAlchemyUnitOfWork(database) as uow:
        await uow.secrets.add(Secret(id=secret_id, account_id="acc", ciphertext=b"\x00\x01\x02"))
        await uow.commit()

    async with SqlAlchemyUnitOfWork(database) as uow:
        fetched = await uow.secrets.get(secret_id)

    assert fetched.ciphertext == b"\x00\x01\x02"
    assert fetched.account_id == "acc"
    assert fetched.version == 1


async def test_rollback_discards_uncommitted_write(database):
    secret_id = uuid4()
    async with SqlAlchemyUnitOfWork(database) as uow:
        await uow.secrets.add(Secret(id=secret_id, account_id="acc", ciphertext=b"x"))
        await uow.rollback()

    async with SqlAlchemyUnitOfWork(database) as uow:
        with pytest.raises(SecretNotFound):
            await uow.secrets.get(secret_id)


async def test_activity_counts_latest_mutations_and_scopes_account(database):
    from datetime import UTC, datetime

    account_id = str(uuid4())
    event_time = datetime(2026, 7, 14, 12, tzinfo=UTC)
    async with SqlAlchemyUnitOfWork(database) as uow:
        await uow.secrets.add(
            Secret(uuid4(), account_id, b"created", version=1, updated_at=event_time)
        )
        await uow.secrets.add(
            Secret(uuid4(), account_id, b"updated", version=2, updated_at=event_time)
        )
        await uow.secrets.add(
            Secret(uuid4(), account_id, b"deleted", version=2, deleted=True, updated_at=event_time)
        )
        await uow.secrets.add(
            Secret(uuid4(), "other-account", b"other", version=1, updated_at=event_time)
        )
        await uow.commit()

    async with SqlAlchemyUnitOfWork(database) as uow:
        counts = await uow.secrets.activity_counts(
            account_id,
            start_at=datetime(2026, 7, 14, tzinfo=UTC),
            end_at=datetime(2026, 7, 15, tzinfo=UTC),
        )

    assert len(counts) == 1
    assert counts[0].date.isoformat() == "2026-07-14"
    assert (counts[0].created, counts[0].updated, counts[0].deleted) == (1, 1, 1)
