"""SQLAlchemy implementation of the IdentityRepository port."""

from typing import Any

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

from gophkeeper.domain.identity import AccountIdentity, IdentityRepository

_COLUMNS = ("id", "account_id", "provider", "identifier", "secret", "created_at")
_COLUMN_LIST = ", ".join(_COLUMNS)
_INSERT_VALUES = ", ".join(f":{c}" for c in _COLUMNS)


def _to_params(identity: AccountIdentity) -> dict[str, Any]:
    return {
        "id": identity.id,
        "account_id": identity.account_id,
        "provider": identity.provider,
        "identifier": identity.identifier,
        "secret": identity.secret,
        "created_at": identity.created_at,
    }


def _from_row(row: RowMapping) -> AccountIdentity:
    return AccountIdentity(
        id=row["id"],
        account_id=row["account_id"],
        provider=row["provider"],
        identifier=row["identifier"],
        secret=row["secret"],
        created_at=row["created_at"],
    )


class SqlAlchemyIdentityRepository(IdentityRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, identity: AccountIdentity) -> None:
        await self._session.execute(
            text(f"INSERT INTO account_identities ({_COLUMN_LIST}) VALUES ({_INSERT_VALUES})"),
            _to_params(identity),
        )

    async def find(self, provider: str, identifier: str) -> AccountIdentity | None:
        result = await self._session.execute(
            text(
                f"SELECT {_COLUMN_LIST} FROM account_identities "
                "WHERE provider = :provider AND identifier = :identifier"
            ),
            {"provider": provider, "identifier": identifier},
        )
        row = result.mappings().first()
        return _from_row(row) if row is not None else None
