"""SQLAlchemy implementation of the SecretRepository port.

EXAMPLE adapter. It translates between the ``Secret`` domain object and the
``secrets`` table. We use SQLAlchemy Core text queries (not the ORM): the domain
model stays a plain dataclass with no mapper, and the mapping is explicit and
visible right here. New aggregates get a sibling adapter following this shape.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

from gophkeeper.domain.errors import SecretNotFound, VersionConflict
from gophkeeper.domain.secret import Secret, SecretActivityCount, SecretRepository

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
            text(f"INSERT INTO secrets ({_INSERT_LIST}) VALUES ({_INSERT_VALUES}) RETURNING seq"),
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
        self, account_id: str, device_id: UUID, since_seq: int, *, limit: int
    ) -> list[Secret]:
        result = await self._session.execute(
            text(
                f"SELECT {_READ_LIST} FROM secrets s "
                "JOIN secret_recipients sr ON sr.secret_id = s.id "
                "WHERE s.account_id = :account_id AND sr.device_id = :device_id "
                "AND s.seq > :since_seq ORDER BY s.seq LIMIT :limit"
            ),
            {
                "account_id": account_id,
                "device_id": device_id,
                "since_seq": since_seq,
                "limit": limit,
            },
        )
        return [_from_row(row) for row in result.mappings().all()]

    async def activity_counts(
        self, account_id: str, *, start_at: datetime, end_at: datetime
    ) -> list[SecretActivityCount]:
        """Count each secret's latest persisted mutation, grouped by UTC day.

        The table stores a current snapshot rather than an event log. Consequently,
        this query cannot reconstruct superseded mutations or an original creation
        date after a secret has been updated.
        """
        result = await self._session.execute(
            text(
                "SELECT (updated_at AT TIME ZONE 'UTC')::date AS activity_date, "
                "COUNT(*) FILTER (WHERE version = 1 AND NOT deleted) AS created, "
                "COUNT(*) FILTER (WHERE version > 1 AND NOT deleted) AS updated, "
                "COUNT(*) FILTER (WHERE deleted) AS deleted "
                "FROM secrets "
                "WHERE account_id = :account_id "
                "AND updated_at >= :start_at AND updated_at < :end_at "
                "GROUP BY activity_date ORDER BY activity_date"
            ),
            {"account_id": account_id, "start_at": start_at, "end_at": end_at},
        )
        return [
            SecretActivityCount(
                date=row["activity_date"],
                created=row["created"],
                updated=row["updated"],
                deleted=row["deleted"],
            )
            for row in result.mappings().all()
        ]

    async def set_recipients(self, secret_id: UUID, device_ids: list[UUID]) -> None:
        await self._session.execute(
            text("DELETE FROM secret_recipients WHERE secret_id = :secret_id"),
            {"secret_id": secret_id},
        )
        for device_id in device_ids:
            await self._session.execute(
                text(
                    "INSERT INTO secret_recipients (secret_id, device_id) "
                    "VALUES (:secret_id, :device_id)"
                ),
                {"secret_id": secret_id, "device_id": device_id},
            )

    async def save(self, secret: Secret, *, expected_version: int | None = None) -> None:
        set_clause = (
            "ciphertext = :ciphertext, version = :version, "
            "deleted = :deleted, updated_at = :updated_at, "
            "seq = nextval('secret_seq') "
        )
        if expected_version is None:
            # Unconditional write (tombstone): the row is known to exist.
            result = await self._session.execute(
                text(f"UPDATE secrets SET {set_clause} WHERE id = :id RETURNING seq"),
                _to_params(secret),
            )
            secret.seq = result.scalar_one()
            return

        # Compare-and-set: the UPDATE only matches if the stored version is still
        # the one the client edited. Concurrent pushes can no longer both read
        # v1, both pass an in-app check, and both blindly write v2.
        result = await self._session.execute(
            text(
                f"UPDATE secrets SET {set_clause} "
                "WHERE id = :id AND version = :expected_version RETURNING seq"
            ),
            {**_to_params(secret), "expected_version": expected_version},
        )
        seq = result.scalar_one_or_none()
        if seq is None:
            current = await self.get(secret.id)
            raise VersionConflict(secret.id, expected=expected_version, actual=current.version)
        secret.seq = seq
