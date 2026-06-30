"""Integration tests for SecretRepository."""

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
