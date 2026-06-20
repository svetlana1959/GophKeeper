"""SQLAlchemy implementation of the DeviceRepository port.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

from gophkeeper.domain.errors import DeviceNotFound
from gophkeeper.domain.device import Device, DeviceRepository

_COLUMNS = "id, device_name, public_key, is_active, updated_at"


def _to_params(device: Device) -> dict[str, Any]:
    return {
        # BUG FIX: same root cause as secret_repository.py — the `id` column
        # in this database is TEXT, not UUID (an older migration created it
        # before the domain model switched to UUID). Passing a plain str
        # instead of a UUID-typed bind param works against either column
        # type, since Postgres implicitly casts a string literal when
        # comparing it to a uuid column.
        "id": str(device.id),
        "device_name": device.device_name,
        "public_key": device.public_key,
        "is_active": device.is_active,
        "updated_at": device.updated_at,
    }


def _from_row(row: RowMapping) -> Device:
    return Device(
        id=UUID(str(row["id"])),
        device_name=row["device_name"],
        public_key=row["public_key"],
        is_active=bool(row["is_active"]),
        updated_at=row["updated_at"],
    )


class SqlAlchemyDeviceRepository(DeviceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, device: Device) -> None:
        await self._session.execute(
            text(
                f"INSERT INTO devices ({_COLUMNS}) "
                "VALUES (:id, :device_name, :public_key, :is_active, :updated_at)"
            ),
            _to_params(device),
        )

    async def get(self, device_id: UUID) -> Device:
        result = await self._session.execute(
            text(f"SELECT {_COLUMNS} FROM devices WHERE id = :id"),
            {"id": str(device_id)},
        )
        row = result.mappings().first()
        if row is None:
            raise DeviceNotFound(device_id)
        return _from_row(row)

    async def exists(self, device_id: UUID) -> bool:
        result = await self._session.execute(
            text("SELECT 1 FROM devices WHERE id = :id"),
            {"id": str(device_id)},
        )
        return result.first() is not None

    async def list_active(self) -> list[Device]:
        query = f"SELECT {_COLUMNS} FROM devices WHERE is_active = TRUE ORDER BY device_name"
        result = await self._session.execute(text(query))
        return [_from_row(row) for row in result.mappings().all()]

    async def save(self, device: Device) -> None:
        await self._session.execute(
            text(
                "UPDATE devices SET "
                "device_name = :device_name, "
                "public_key = :public_key, "
                "is_active = :is_active, "
                "updated_at = :updated_at "
                "WHERE id = :id"
            ),
            _to_params(device),
        )
