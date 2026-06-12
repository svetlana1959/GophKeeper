"""
store.repository.local_device
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Repository for the ``local_device`` table (exactly one row per installation).

The private key is stored as an opaque ``bytes`` blob — either:
- PIN-encrypted  (Argon2id/scrypt + AEAD) when the user set a PIN during ``init``.
- Raw AGE private key bytes when no PIN was set (file-permission 0600 is the guard).

This layer never derives, encrypts, or decrypts the key; that is the caller's job.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional

from store.models import LocalDevice


class LocalDeviceRepository:
    """Store and retrieve the local device's identity row.

    There is at most **one** row in ``local_device`` at any time.

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

    def save(self, local_device: LocalDevice) -> None:
        """Insert or replace the local device record.

        Uses ``INSERT OR REPLACE`` so that calling ``save`` a second time
        (e.g. after rotating the PIN) updates the stored key in place.

        The corresponding ``trusted_devices`` row **must** exist before
        calling this method (foreign-key constraint).
        """
        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO local_device
                    (device_id, private_key_encrypted, created_at)
                VALUES (?, ?, ?)
                """,
                (
                    local_device.device_id,
                    local_device.private_key_encrypted,
                    local_device.created_at.isoformat(),
                ),
            )

    def update_private_key(self, device_id: str, private_key_encrypted: bytes) -> None:
        """Replace only the stored private key blob (e.g. after a PIN change).

        Does nothing if the row does not exist.
        """
        with self._conn:
            self._conn.execute(
                """
                UPDATE local_device
                   SET private_key_encrypted = ?
                 WHERE device_id = ?
                """,
                (private_key_encrypted, device_id),
            )

    def delete(self, device_id: str) -> None:
        """Remove the local device record (also removes trusted_devices row via CASCADE)."""
        with self._conn:
            self._conn.execute(
                "DELETE FROM local_device WHERE device_id = ?",
                (device_id,),
            )

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get(self) -> Optional[LocalDevice]:
        """Return the single local device row, or *None* if not initialised yet."""
        row = self._conn.execute(
            "SELECT * FROM local_device LIMIT 1"
        ).fetchone()
        return _row_to_model(row) if row else None

    def get_by_id(self, device_id: str) -> Optional[LocalDevice]:
        """Return the local device row for a specific device_id."""
        row = self._conn.execute(
            "SELECT * FROM local_device WHERE device_id = ?",
            (device_id,),
        ).fetchone()
        return _row_to_model(row) if row else None

    def exists(self) -> bool:
        """Return *True* when a local device has been initialised."""
        row = self._conn.execute(
            "SELECT 1 FROM local_device LIMIT 1"
        ).fetchone()
        return row is not None


# ---------------------------------------------------------------------------
# Mapping helper
# ---------------------------------------------------------------------------

def _row_to_model(row: sqlite3.Row) -> LocalDevice:
    raw_key = row["private_key_encrypted"]
    # sqlite3 returns BLOB columns as bytes; TEXT columns as str.
    # Normalise to bytes in either case.
    if isinstance(raw_key, str):
        raw_key = raw_key.encode()
    return LocalDevice(
        device_id=row["device_id"],
        private_key_encrypted=raw_key,
        created_at=_parse_dt(row["created_at"]),
    )


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    return datetime.fromisoformat(value)
