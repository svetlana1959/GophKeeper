"""SQLAlchemy implementation of the AccessRequestRepository port.

Translates between the ``AccessRequest`` domain object and the
``access_requests`` table. Plain ``text()`` queries, same shape as every other
repository in this package.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import RowMapping, text
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
        # BUG AVOIDED: catching IntegrityError here and calling
        # session.rollback() would roll back the *entire* UnitOfWork
        # transaction, not just this insert — any other work already done
        # in the same use case would be silently discarded too. Checking
        # for an existing PENDING row up front keeps this method's failure
        # mode local to itself, with no special transaction handling needed.
        # The partial unique index in the migration remains the real
        # guarantee against a race between two concurrent requests; this
        # check only gives a clean domain error in the common, non-racing
        # case.
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

        await self._session.execute(
            text(f"INSERT INTO access_requests ({_COLUMN_LIST}) VALUES ({_INSERT_VALUES})"),
            _to_params(request),
        )

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
