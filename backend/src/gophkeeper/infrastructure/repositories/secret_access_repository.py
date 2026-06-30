"""SQLAlchemy implementation of the SecretAccessRepository port.

Reads and writes the ``secret_access`` table with Core ``text()`` queries, same
shape as every other repository in this package.
"""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from gophkeeper.domain.secret import SecretAccessRepository

_COLUMNS = ("secret_id", "device_id")
_COLUMN_LIST = ", ".join(_COLUMNS)
_INSERT_VALUES = ", ".join(f":{c}" for c in _COLUMNS)


def _to_params(secret_id: UUID, device_id: UUID) -> dict[str, UUID]:
    return {
        "secret_id": secret_id,
        "device_id": device_id,
    }


class SqlAlchemySecretAccessRepository(SecretAccessRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def grant(self, secret_id: UUID, device_id: UUID) -> None:
        await self._session.execute(
            text(
                f"INSERT INTO secret_access ({_COLUMN_LIST}) "
                f"VALUES ({_INSERT_VALUES}) "
                "ON CONFLICT (secret_id, device_id) DO NOTHING"
            ),
            _to_params(secret_id, device_id),
        )

    async def has_access(self, secret_id: UUID, device_id: UUID) -> bool:
        result = await self._session.execute(
            text(
                "SELECT 1 FROM secret_access "
                "WHERE secret_id = :secret_id AND device_id = :device_id"
            ),
            _to_params(secret_id, device_id),
        )
        return result.first() is not None

    async def list_secret_ids_for_device(self, device_id: UUID) -> list[UUID]:
        result = await self._session.execute(
            text("SELECT secret_id FROM secret_access WHERE device_id = :device_id"),
            {"device_id": device_id},
        )
        return [row[0] for row in result.all()]
