"""SQLAlchemy implementation of the AccessRequestRepository port.

Translates between the ``AccessRequest`` domain object and the
``access_requests`` table. Plain ``text()`` queries, same shape as every other
repository in this package.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import RowMapping, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from gophkeeper.domain.access_request import (
    AccessRequest,
    AccessRequestRepository,
    AccessRequestStatus,
)
from gophkeeper.domain.errors import AccessRequestAlreadyPending, AccessRequestNotFound

_COLUMNS = ("id", "secret_id", "device_id", "status", "updated_at")
_COLUMN_LIST = ", ".join(_COLUMNS)
_INSERT_VALUES = ", ".join(f":{c}" for c in _COLUMNS)


def _to_params(request: AccessRequest) -> dict[str, Any]:
    return {
        "id": request.id,
        "secret_id": request.secret_id,
        "device_id": request.device_id,
        "status": request.status.value,
        "updated_at": request.updated_at,
    }


def _from_row(row: RowMapping) -> AccessRequest:
    return AccessRequest(
        id=row["id"],
        secret_id=row["secret_id"],
        device_id=row["device_id"],
        status=AccessRequestStatus(row["status"]),
        updated_at=row["updated_at"],
    )


class SqlAlchemyAccessRequestRepository(AccessRequestRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, request: AccessRequest) -> None:
        # The upfront SELECT below closes the common, non-racing case with a
        # clean domain error. It is NOT sufficient on its own: two concurrent
        # requests for the same (secret_id, device_id) can both pass the
        # SELECT before either INSERTs, a classic check-then-act race. The
        # partial unique index in the migration is what actually prevents two
        # PENDING rows from existing — the loser of the race hits it on
        # INSERT and gets a raw IntegrityError, which we catch here and
        # re-raise as the same domain error the SELECT path raises, so the
        # caller sees one consistent error either way.
        #
        # Importantly we do NOT call session.rollback() ourselves here: that
        # would discard the whole Unit-of-Work transaction, not just this
        # insert. We let the exception propagate instead — the caller's
        # `async with self._uow as uow:` block in the service layer exits
        # via SqlAlchemyUnitOfWork.__aexit__, which already rolls back
        # automatically on any exception. This mirrors exactly how
        # VersionConflict is handled elsewhere in this codebase.
        existing = await self._session.execute(
            text(
                "SELECT 1 FROM access_requests "
                "WHERE secret_id = :secret_id AND device_id = :device_id "
                "AND status = 'PENDING'"
            ),
            {"secret_id": request.secret_id, "device_id": request.device_id},
        )
        if existing.first() is not None:
            raise AccessRequestAlreadyPending(request.secret_id, request.device_id)

        try:
            await self._session.execute(
                text(f"INSERT INTO access_requests ({_COLUMN_LIST}) VALUES ({_INSERT_VALUES})"),
                _to_params(request),
            )
            await self._session.flush()
        except IntegrityError as exc:
            raise AccessRequestAlreadyPending(request.secret_id, request.device_id) from exc

    async def get(self, request_id: UUID) -> AccessRequest:
        result = await self._session.execute(
            text(f"SELECT {_COLUMN_LIST} FROM access_requests WHERE id = :id"),
            {"id": request_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AccessRequestNotFound(request_id)
        return _from_row(row)

    async def list_pending_for_secret(self, secret_id: UUID) -> list[AccessRequest]:
        result = await self._session.execute(
            text(
                f"SELECT {_COLUMN_LIST} FROM access_requests "
                "WHERE secret_id = :secret_id AND status = 'PENDING' "
                "ORDER BY updated_at"
            ),
            {"secret_id": secret_id},
        )
        return [_from_row(row) for row in result.mappings().all()]

    async def save(self, request: AccessRequest) -> None:
        await self._session.execute(
            text(
                "UPDATE access_requests SET status = :status, updated_at = :updated_at "
                "WHERE id = :id"
            ),
            {"id": request.id, "status": request.status.value, "updated_at": request.updated_at},
        )
