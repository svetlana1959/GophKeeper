"""SQLAlchemy implementation of the DeviceRepository port."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

from gophkeeper.domain.device import Device, DeviceRepository
from gophkeeper.domain.errors import DeviceNotFound

_COLUMNS = (
    "id",
    "account_id",
    "device_name",
    "public_key",
    "sign_public_key",
    "status",
    "last_seen_at",
    "expires_at",
    "updated_at",
)
_COLUMN_LIST = ", ".join(_COLUMNS)
_INSERT_VALUES = ", ".join(f":{c}" for c in _COLUMNS)


def _to_params(device: Device) -> dict[str, Any]:
    return {
        "id": device.id,
        "account_id": device.account_id,
        "device_name": device.device_name,
        "public_key": device.public_key,
        "sign_public_key": device.sign_public_key,
        "status": device.status,
        "last_seen_at": device.last_seen_at,
        "expires_at": device.expires_at,
        "updated_at": device.updated_at,
    }


def _from_row(row: RowMapping) -> Device:
    return Device(
        id=row["id"],
        account_id=row["account_id"],
        device_name=row["device_name"],
        public_key=row["public_key"],
        sign_public_key=row["sign_public_key"],
        status=row["status"],
        last_seen_at=row["last_seen_at"],
        expires_at=row["expires_at"],
        updated_at=row["updated_at"],
    )


class SqlAlchemyDeviceRepository(DeviceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, device: Device) -> None:
        await self._session.execute(
            text(f"INSERT INTO devices ({_COLUMN_LIST}) VALUES ({_INSERT_VALUES})"),
            _to_params(device),
        )

    async def get(self, device_id: UUID) -> Device:
        result = await self._session.execute(
            text(f"SELECT {_COLUMN_LIST} FROM devices WHERE id = :id"),
            {"id": device_id},
        )
        row = result.mappings().first()
        if row is None:
            raise DeviceNotFound(device_id)
        return _from_row(row)

    async def find_by_public_key(self, public_key: str) -> Device | None:
        result = await self._session.execute(
            text(f"SELECT {_COLUMN_LIST} FROM devices WHERE public_key = :public_key"),
            {"public_key": public_key},
        )
        row = result.mappings().first()
        return _from_row(row) if row is not None else None

    async def exists(self, device_id: UUID) -> bool:
        result = await self._session.execute(
            text("SELECT 1 FROM devices WHERE id = :id"),
            {"id": device_id},
        )
        return result.first() is not None

    async def list_for_account(self, account_id: UUID) -> list[Device]:
        result = await self._session.execute(
            text(
                f"SELECT {_COLUMN_LIST} FROM devices "
                "WHERE account_id = :account_id ORDER BY device_name"
            ),
            {"account_id": account_id},
        )
        return [_from_row(row) for row in result.mappings().all()]

    async def save(self, device: Device) -> None:
        await self._session.execute(
            text(
                "UPDATE devices SET "
                "account_id = :account_id, "
                "device_name = :device_name, "
                "public_key = :public_key, "
                "sign_public_key = :sign_public_key, "
                "status = :status, "
                "last_seen_at = :last_seen_at, "
                "expires_at = :expires_at, "
                "updated_at = :updated_at "
                "WHERE id = :id"
            ),
            _to_params(device),
        )

    async def delete(self, device_id: UUID) -> None:
        """Hard-delete a single device by id. Cascades clean up its recipient rows
        and issued trust certs. Idempotent — deleting an absent id is a no-op."""
        await self._session.execute(
            text("DELETE FROM devices WHERE id = :id"),
            {"id": device_id},
        )

    async def delete_expired(self, *, now: datetime) -> int:
        """Hard-delete every device past its declared expiry, returning the count.

        Devices with no expiry (``expires_at IS NULL``) are never touched. The
        secret_recipients and trust_certs foreign keys cascade, so a reaped
        device leaves no dangling rows behind.
        """
        result = await self._session.execute(
            text("DELETE FROM devices WHERE expires_at IS NOT NULL AND expires_at < :now"),
            {"now": now},
        )
        return result.rowcount or 0

    async def delete_inactive(self, *, cutoff: datetime) -> int:
        """Hard-delete every idle device *whose account has a recovery key*,
        returning the count. A never-authenticated device falls back to when it
        was created (``updated_at``).

        The recovery-key guard is load-bearing, not a nicety: deleting a device
        cascades its secret_recipients (and any trust certs it issued). Reaping
        the last device of an account with no recovery key would leave ciphertext
        no one can decrypt — irrecoverable. Restricting the backstop to accounts
        that CAN restore via the recovery key keeps every vault recoverable, and
        those accounts restore through the recovery key rather than the (now
        gappy) server trust log."""
        result = await self._session.execute(
            text(
                "DELETE FROM devices d "
                "WHERE COALESCE(d.last_seen_at, d.updated_at) < :cutoff "
                "AND EXISTS ("
                "  SELECT 1 FROM accounts a "
                "  WHERE a.id = d.account_id AND a.recovery_pubkey IS NOT NULL"
                ")"
            ),
            {"cutoff": cutoff},
        )
        return result.rowcount or 0
