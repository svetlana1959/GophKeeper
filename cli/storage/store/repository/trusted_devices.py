"""
store.repository.trusted_devices
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Repository for the ``trusted_devices`` table.

Provides full CRUD plus activate / deactivate helpers.
No business logic — SQL only.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional

from store.models import TrustedDevice


class TrustedDeviceRepository:
    """CRUD + lifecycle operations for trusted_devices rows.

    Parameters
    ----------
    conn:
        An open :class:`sqlite3.Connection` supplied by :class:`DBAdapter`.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def add(self, device: TrustedDevice) -> None:
        """Insert a new trusted device.

        Raises
        ------
        sqlite3.IntegrityError
            If a device with the same ``id`` already exists.
        """
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO trusted_devices (id, device_name, public_key, is_active, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    device.id,
                    device.device_name,
                    device.public_key,
                    int(device.is_active),
                    device.updated_at.isoformat(),
                ),
            )

    def update(self, device: TrustedDevice) -> None:
        """Update device_name, public_key, and is_active for an existing device.

        ``updated_at`` is refreshed automatically.
        """
        with self._conn:
            self._conn.execute(
                """
                UPDATE trusted_devices
                   SET device_name = ?,
                       public_key  = ?,
                       is_active   = ?,
                       updated_at  = ?
                 WHERE id = ?
                """,
                (
                    device.device_name,
                    device.public_key,
                    int(device.is_active),
                    datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                    device.id,
                ),
            )

    def delete(self, device_id: str) -> None:
        """Hard-delete a device row (cascades to local_device + secret_recipients)."""
        with self._conn:
            self._conn.execute(
                "DELETE FROM trusted_devices WHERE id = ?",
                (device_id,),
            )

    def activate(self, device_id: str) -> None:
        """Set is_active = 1 for the given device."""
        self._set_active(device_id, active=True)

    def deactivate(self, device_id: str) -> None:
        """Set is_active = 0 (revoke) for the given device."""
        self._set_active(device_id, active=False)

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get(self, device_id: str) -> Optional[TrustedDevice]:
        """Return a single device by primary key, or *None* if not found."""
        row = self._conn.execute(
            "SELECT * FROM trusted_devices WHERE id = ?",
            (device_id,),
        ).fetchone()
        return _row_to_model(row) if row else None

    def get_by_name(self, device_name: str) -> Optional[TrustedDevice]:
        """Return the first device matching *device_name*, or *None*."""
        row = self._conn.execute(
            "SELECT * FROM trusted_devices WHERE device_name = ?",
            (device_name,),
        ).fetchone()
        return _row_to_model(row) if row else None

    def list_all(self) -> list[TrustedDevice]:
        """Return all devices (active and revoked)."""
        rows = self._conn.execute(
            "SELECT * FROM trusted_devices ORDER BY updated_at DESC"
        ).fetchall()
        return [_row_to_model(r) for r in rows]

    def list_active(self) -> list[TrustedDevice]:
        """Return only active (non-revoked) devices."""
        rows = self._conn.execute(
            "SELECT * FROM trusted_devices WHERE is_active = 1 ORDER BY updated_at DESC"
        ).fetchall()
        return [_row_to_model(r) for r in rows]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _set_active(self, device_id: str, *, active: bool) -> None:
        with self._conn:
            self._conn.execute(
                """
                UPDATE trusted_devices
                   SET is_active = ?, updated_at = ?
                 WHERE id = ?
                """,
                (int(active), datetime.now(timezone.utc).replace(tzinfo=None).isoformat(), device_id),
            )


# ---------------------------------------------------------------------------
# Mapping helper
# ---------------------------------------------------------------------------

def _row_to_model(row: sqlite3.Row) -> TrustedDevice:
    return TrustedDevice(
        id=row["id"],
        device_name=row["device_name"],
        public_key=row["public_key"],
        is_active=bool(row["is_active"]),
        updated_at=_parse_dt(row["updated_at"]),
    )


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    # SQLite stores datetimes as ISO-8601 strings
    return datetime.fromisoformat(value)
