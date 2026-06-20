"""SQLAlchemy implementation of the SecretRepository port.

EXAMPLE adapter. It translates between the ``Secret`` domain object and the
``secrets`` table. We use SQLAlchemy Core text queries (not the ORM): the domain
model stays a plain dataclass with no mapper, and the mapping is explicit and
visible right here. New aggregates get a sibling adapter following this shape.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

from gophkeeper.domain.errors import SecretNotFound
from gophkeeper.domain.secret import Secret, SecretRepository

_COLUMNS = "id, account_id, ciphertext, version, deleted, updated_at"


def _to_params(secret: Secret) -> dict[str, Any]:
    return {
        # BUG FIX: send the id as plain str, not a UUID object or an
        # explicitly UUID-typed bind param. The `id` column in this database
        # is TEXT (an older migration ran before the domain switched to
        # UUID), so an explicit ::UUID cast on the parameter caused Postgres
        # to compare "text = uuid", which has no operator. A plain string
        # parameter compares fine against either a TEXT or a UUID column —
        # Postgres implicitly casts a string literal when comparing to uuid.
        "id": str(secret.id),
        "account_id": secret.account_id,
        "ciphertext": secret.ciphertext,
        "version": secret.version,
        "deleted": secret.deleted,
        "updated_at": secret.updated_at,
    }


def _from_row(row: RowMapping) -> Secret:
    return Secret(
        id=UUID(str(row["id"])),
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
            text(
                f"INSERT INTO secrets ({_COLUMNS}) "
                "VALUES (:id, :account_id, :ciphertext, :version, :deleted, :updated_at)"
            ),
            _to_params(secret),
        )

    async def get(self, secret_id: UUID) -> Secret:
        result = await self._session.execute(
            text(f"SELECT {_COLUMNS} FROM secrets WHERE id = :id"),
            {"id": str(secret_id)},
        )
        row = result.mappings().first()
        if row is None:
            raise SecretNotFound(secret_id)
        return _from_row(row)

    async def list_for_account(
        self, account_id: str, *, include_deleted: bool = False
    ) -> list[Secret]:
        query = f"SELECT {_COLUMNS} FROM secrets WHERE account_id = :account_id"
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
