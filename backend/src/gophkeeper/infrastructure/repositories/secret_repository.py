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

# seq is excluded from writes: the DB assigns it (default nextval on insert,
# nextval explicitly on update) and we read it back via RETURNING.
_WRITE_COLUMNS = ("id", "account_id", "ciphertext", "version", "deleted", "updated_at")
_INSERT_LIST = ", ".join(_WRITE_COLUMNS)
_INSERT_VALUES = ", ".join(f":{c}" for c in _WRITE_COLUMNS)
_READ_LIST = ", ".join((*_WRITE_COLUMNS, "seq"))


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
        seq=row["seq"],
    )


class SqlAlchemySecretRepository(SecretRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, secret: Secret) -> None:
        result = await self._session.execute(
            text(
                f"INSERT INTO secrets ({_INSERT_LIST}) VALUES ({_INSERT_VALUES}) RETURNING seq"
            ),
            _to_params(secret),
        )
        secret.seq = result.scalar_one()

    async def get(self, secret_id: UUID) -> Secret:
        result = await self._session.execute(
            text(f"SELECT {_READ_LIST} FROM secrets WHERE id = :id"),
            {"id": secret_id},
        )
        row = result.mappings().first()
        if row is None:
            raise SecretNotFound(secret_id)
        return _from_row(row)

    async def list_for_account(
        self, account_id: str, *, include_deleted: bool = False
    ) -> list[Secret]:
        query = f"SELECT {_READ_LIST} FROM secrets WHERE account_id = :account_id"
        if not include_deleted:
            query += " AND deleted = FALSE"
        query += " ORDER BY id"
        result = await self._session.execute(text(query), {"account_id": account_id})
        return [_from_row(row) for row in result.mappings().all()]

    async def list_changed_since(
        self, account_id: str, since_seq: int, *, limit: int
    ) -> list[Secret]:
        result = await self._session.execute(
            text(
                f"SELECT {_READ_LIST} FROM secrets "
                "WHERE account_id = :account_id AND seq > :since_seq "
                "ORDER BY seq LIMIT :limit"
            ),
            {"account_id": account_id, "since_seq": since_seq, "limit": limit},
        )
        return [_from_row(row) for row in result.mappings().all()]

    async def save(self, secret: Secret) -> None:
        result = await self._session.execute(
            text(
                "UPDATE secrets SET "
                "ciphertext = :ciphertext, version = :version, "
                "deleted = :deleted, updated_at = :updated_at, "
                "seq = nextval('secret_seq') "
                "WHERE id = :id RETURNING seq"
            ),
            _to_params(secret),
        )
        secret.seq = result.scalar_one()
