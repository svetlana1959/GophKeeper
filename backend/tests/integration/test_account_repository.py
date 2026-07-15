"""Integration tests for AccountRepository."""

from uuid import uuid4

import pytest

from gophkeeper.domain.account import Account
from gophkeeper.domain.errors import AccountNotFound
from gophkeeper.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


async def test_update_sets_recovery_pubkey(database):
    account_id = uuid4()
    async with SqlAlchemyUnitOfWork(database) as uow:
        await uow.accounts.add(Account(id=account_id))
        await uow.commit()

    async with SqlAlchemyUnitOfWork(database) as uow:
        account = await uow.accounts.get(account_id)
        assert account.recovery_pubkey is None
        account.recovery_pubkey = "age1recoverypublickey"
        await uow.accounts.update(account)
        await uow.commit()

    async with SqlAlchemyUnitOfWork(database) as uow:
        fetched = await uow.accounts.get(account_id)

    assert fetched.recovery_pubkey == "age1recoverypublickey"


async def test_update_unknown_account_raises(database):
    async with SqlAlchemyUnitOfWork(database) as uow:
        with pytest.raises(AccountNotFound):
            await uow.accounts.update(Account(id=uuid4(), recovery_pubkey="age1nope"))
