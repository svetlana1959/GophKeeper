"""SQLAlchemy implementation of the InviteRepository port."""

from typing import Any

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

from gophkeeper.domain.invite import Invite, InviteRepository

_COLUMNS = ("id", "account_id", "code_hash", "expires_at", "consumed_at", "created_at")
_COLUMN_LIST = ", ".join(_COLUMNS)
_INSERT_VALUES = ", ".join(f":{c}" for c in _COLUMNS)


def _to_params(invite: Invite) -> dict[str, Any]:
    return {
        "id": invite.id,
        "account_id": invite.account_id,
        "code_hash": invite.code_hash,
        "expires_at": invite.expires_at,
        "consumed_at": invite.consumed_at,
        "created_at": invite.created_at,
    }


def _from_row(row: RowMapping) -> Invite:
    return Invite(
        id=row["id"],
        account_id=row["account_id"],
        code_hash=row["code_hash"],
        expires_at=row["expires_at"],
        consumed_at=row["consumed_at"],
        created_at=row["created_at"],
    )


class SqlAlchemyInviteRepository(InviteRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, invite: Invite) -> None:
        await self._session.execute(
            text(f"INSERT INTO invites ({_COLUMN_LIST}) VALUES ({_INSERT_VALUES})"),
            _to_params(invite),
        )

    async def find_by_code_hash(self, code_hash: str) -> Invite | None:
        result = await self._session.execute(
            text(f"SELECT {_COLUMN_LIST} FROM invites WHERE code_hash = :code_hash"),
            {"code_hash": code_hash},
        )
        row = result.mappings().first()
        return _from_row(row) if row is not None else None

    async def save(self, invite: Invite) -> None:
        await self._session.execute(
            text("UPDATE invites SET consumed_at = :consumed_at WHERE id = :id"),
            {"consumed_at": invite.consumed_at, "id": invite.id},
        )
