"""Narrow SecretRepository tests — SQL the HTTP API can't exercise.

Two things live here because the API can't reach them cleanly:

* ``get`` — its ``SecretNotFound`` branch is swallowed inside ``SyncService.push``
  (a missing secret becomes a create), so it never surfaces as a response to
  assert on. The stored-then-read path is proven here at the same time.
* ``activity_counts`` — its value is the UTC-day bucketing of ``updated_at``, and
  reaching it through the API would mean back-dating ``updated_at`` (no endpoint
  for that), so the day-grouping SQL is tested directly.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from gophkeeper.domain.errors import SecretNotFound
from gophkeeper.domain.secret import Secret
from gophkeeper.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


async def test_get_returns_stored_secret_or_raises_when_absent(database):
    secret_id = uuid4()
    async with SqlAlchemyUnitOfWork(database) as uow:
        await uow.secrets.add(Secret(secret_id, "acc", ciphertext=b"\x00\x01\x02"))
        await uow.commit()

    async with SqlAlchemyUnitOfWork(database) as uow:
        stored = await uow.secrets.get(secret_id)
        assert stored.ciphertext == b"\x00\x01\x02"
        assert stored.version == 1
        with pytest.raises(SecretNotFound):
            await uow.secrets.get(uuid4())


async def test_uow_rollback_discards_only_pre_rollback_work(database):
    # rollback() must undo work done before it while leaving a later commit intact.
    # Asserting "add then rollback then absent" wouldn't discriminate — closing the
    # session discards uncommitted work regardless — so this rolls back one write,
    # commits a second, and checks that exactly the second survived. A no-op
    # rollback would carry the first into the commit and fail the not-found check.
    discarded, kept = uuid4(), uuid4()
    async with SqlAlchemyUnitOfWork(database) as uow:
        await uow.secrets.add(Secret(discarded, "acc", ciphertext=b"x"))
        await uow.rollback()
        await uow.secrets.add(Secret(kept, "acc", ciphertext=b"y"))
        await uow.commit()

    async with SqlAlchemyUnitOfWork(database) as uow:
        with pytest.raises(SecretNotFound):
            await uow.secrets.get(discarded)
        assert (await uow.secrets.get(kept)).id == kept


async def test_activity_counts_bucket_by_day_and_scope_account(database):
    account_id = str(uuid4())
    day = datetime(2026, 7, 14, 12, tzinfo=UTC)
    async with SqlAlchemyUnitOfWork(database) as uow:
        await uow.secrets.add(Secret(uuid4(), account_id, b"created", version=1, updated_at=day))
        await uow.secrets.add(Secret(uuid4(), account_id, b"updated", version=2, updated_at=day))
        await uow.secrets.add(
            Secret(uuid4(), account_id, b"deleted", version=2, deleted=True, updated_at=day)
        )
        # A secret on another account must not leak into these counts.
        await uow.secrets.add(Secret(uuid4(), "other-account", b"other", version=1, updated_at=day))
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
