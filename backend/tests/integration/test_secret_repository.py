"""Example integration test — exercises the real adapter against PostgreSQL.

Where the unit tests prove the domain rules in isolation, this proves the
infrastructure: that ``SqlAlchemyUnitOfWork`` + ``SqlAlchemySecretRepository``
actually persist and read back through SQL, and that commit/rollback behave.
Skipped unless ``TEST_DATABASE_URL`` is set (see conftest).
"""

import pytest

from gophkeeper.domain.errors import SecretNotFound
from gophkeeper.domain.secret import Secret
from gophkeeper.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


async def test_store_and_fetch_round_trip(database):
    async with SqlAlchemyUnitOfWork(database) as uow:
        await uow.secrets.add(Secret(id="it-1", account_id="acc", ciphertext=b"\x00\x01\x02"))
        await uow.commit()

    async with SqlAlchemyUnitOfWork(database) as uow:
        fetched = await uow.secrets.get("it-1")

    assert fetched.ciphertext == b"\x00\x01\x02"
    assert fetched.account_id == "acc"
    assert fetched.version == 1


async def test_rollback_discards_uncommitted_write(database):
    async with SqlAlchemyUnitOfWork(database) as uow:
        await uow.secrets.add(Secret(id="it-2", account_id="acc", ciphertext=b"x"))
        await uow.rollback()

    async with SqlAlchemyUnitOfWork(database) as uow:
        with pytest.raises(SecretNotFound):
            await uow.secrets.get("it-2")
