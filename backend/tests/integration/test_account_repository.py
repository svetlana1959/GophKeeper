"""Integration tests for AccountRepository."""

from uuid import uuid4

import pytest

from gophkeeper.domain.account import Account
from gophkeeper.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


async def test_store_and_fetch_recovery_public_key(database):
    account = Account(
        id=uuid4(),
        recovery_pubkey="age1recoverypublickey",
    )
    async with SqlAlchemyUnitOfWork(database) as uow:
        await uow.accounts.add(account)
        await uow.commit()

    async with SqlAlchemyUnitOfWork(database) as uow:
        fetched = await uow.accounts.get(account.id)

    assert fetched.id == account.id
    assert fetched.recovery_pubkey == account.recovery_pubkey
