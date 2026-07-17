"""Narrow AccountRepository tests — the update SQL, pinned at the data layer.

The recovery-key flow is also driven through the API (test_error_mapping.py);
these add a direct, focused check of the UPDATE round-trip and of the not-found
guard, which the API can't reach — a caller only ever updates its own,
already-loaded account, so an update against a missing row can't originate there.
"""

from uuid import uuid4

import pytest

from gophkeeper.domain.account import Account
from gophkeeper.domain.errors import AccountNotFound
from gophkeeper.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


async def test_update_persists_recovery_pubkey(database):
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
        assert (await uow.accounts.get(account_id)).recovery_pubkey == "age1recoverypublickey"


async def test_update_unknown_account_raises(database):
    async with SqlAlchemyUnitOfWork(database) as uow:
        with pytest.raises(AccountNotFound):
            await uow.accounts.update(Account(id=uuid4(), recovery_pubkey="age1nope"))
