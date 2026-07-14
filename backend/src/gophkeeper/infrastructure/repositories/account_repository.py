"""SQLAlchemy implementation of the AccountRepository port."""

from uuid import UUID

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

from gophkeeper.domain.account import Account, AccountRepository
from gophkeeper.domain.errors import AccountNotFound

_COLUMNS = ("id", "recovery_pubkey", "created_at")
_COLUMN_LIST = ", ".join(_COLUMNS)
_INSERT_VALUES = ", ".join(f":{c}" for c in _COLUMNS)


def _from_row(row: RowMapping) -> Account:
    return Account(
        id=row["id"],
        recovery_pubkey=row["recovery_pubkey"],
        created_at=row["created_at"],
    )


class SqlAlchemyAccountRepository(AccountRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, account: Account) -> None:
        await self._session.execute(
            text(f"INSERT INTO accounts ({_COLUMN_LIST}) VALUES ({_INSERT_VALUES})"),
            {
                "id": account.id,
                "recovery_pubkey": account.recovery_pubkey,
                "created_at": account.created_at,
            },
        )

    async def get(self, account_id: UUID) -> Account:
        result = await self._session.execute(
            text(f"SELECT {_COLUMN_LIST} FROM accounts WHERE id = :id"),
            {"id": account_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AccountNotFound(account_id)
        return _from_row(row)

    async def update(self, account: Account) -> None:
        result = await self._session.execute(
            text("UPDATE accounts SET recovery_pubkey = :recovery_pubkey WHERE id = :id"),
            {"id": account.id, "recovery_pubkey": account.recovery_pubkey},
        )
        if result.rowcount == 0:
            raise AccountNotFound(account.id)
