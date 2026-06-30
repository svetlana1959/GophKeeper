"""SQLAlchemy implementation of the SecretRepository port."""

from typing import Any
from uuid import UUID

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

from gophkeeper.domain.errors import SecretNotFound
from gophkeeper.domain.secret import Secret, SecretRepository

_COLUMNS = ("id", "account_id", "ciphertext", "version", "deleted", "updated_at")
_COLUMN_LIST = ", ".join(_COLUMNS)
_INSERT_VALUES = ", ".join(f":{c}" for c in _COLUMNS)


def _to_params(secret: Secret) -> dict[str, Any]:
    return {
        "id": secret.id,
        "account_id": secret.account_id,
        "ciphertext": secret.ciphertext,
        "version": secret.version,
        "deleted": secret.deleted,
        "updated_at": secret.updated_at,
    }


def _from_row(row: RowMapping) -> Secret:
    return Secret(
        id=row["id"],
        account_id=row["account_id"],
        ciphertext=bytes(row["ciphertext"]),
        version=row["version"],
        deleted=row["deleted"],
        updated_at=row["updated_at"],
    )


class SqlAlchemySecretRepository(SecretRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, secret: Secret) -> None:
        await self._session.execute(
            text(f"INSERT INTO secrets ({_COLUMN_LIST}) VALUES ({_INSERT_VALUES})"),
            _to_params(secret),
        )

    async def get(self, secret_id: UUID) -> Secret:
        result = await self._session.execute(
            text(f"SELECT {_COLUMN_LIST} FROM secrets WHERE id = :id"),
            {"id": secret_id},
        )
        row = result.mappings().first()
        if row is None:
            raise SecretNotFound(secret_id)
        return _from_row(row)

    async def list_for_account(
        self, account_id: str, *, include_deleted: bool = False
    ) -> list[Secret]:
        query = f"SELECT {_COLUMN_LIST} FROM secrets WHERE account_id = :account_id"
        if not include_deleted:
            query += " AND deleted = FALSE"
        query += " ORDER BY id"
        result = await self._session.execute(text(query), {"account_id": account_id})
        return [_from_row(row) for row in result.mappings().all()]

    async def save(self, secret: Secret) -> None:
        await self._session.execute(
            text(
                "UPDATE secrets SET "
                "ciphertext = :ciphertext, version = :version, "
                "deleted = :deleted, updated_at = :updated_at "
                "WHERE id = :id"
            ),
            _to_params(secret),
        )
