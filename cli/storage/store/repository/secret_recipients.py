"""
store.repository.secret_recipients
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Repository for the ``secret_recipients`` junction table.

Each row holds one wrapped copy of a secret's Data-Encryption Key (DEK),
asymmetrically encrypted for a specific device's AGE public key.
Only that device can unwrap the DEK and subsequently decrypt the secret.

Operations
----------
* ``add``                 — store a wrapped DEK for one (secret, device) pair.
* ``add_many``            — bulk-insert multiple recipients in one transaction.
* ``get``                 — fetch one recipient record.
* ``list_by_secret``      — all devices that can decrypt a given secret.
* ``list_by_device``      — all secrets accessible to a given device.
* ``remove``              — remove one (secret, device) pair.
* ``remove_all_for_secret`` — remove every recipient row for a secret (e.g. before re-wrapping).
"""

from __future__ import annotations

import sqlite3

from store.models import SecretRecipient


class SecretRecipientRepository:
    """Add / list / remove recipient rows for the ``secret_recipients`` table.

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

    def add(self, recipient: SecretRecipient) -> None:
        """Insert a single (secret_id, device_id, encrypted_dek) triplet.

        Uses ``INSERT OR REPLACE`` so that re-wrapping a DEK for the same
        device simply updates the stored blob.
        """
        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO secret_recipients
                    (secret_id, device_id, encrypted_dek)
                VALUES (?, ?, ?)
                """,
                (
                    recipient.secret_id,
                    recipient.device_id,
                    recipient.encrypted_dek,
                ),
            )

    def add_many(self, recipients: list[SecretRecipient]) -> None:
        """Insert multiple recipient rows in a single transaction.

        Useful when a secret is created and shared with several devices at once.
        Uses ``INSERT OR REPLACE`` — same semantics as :pymeth:`add`.
        """
        with self._conn:
            self._conn.executemany(
                """
                INSERT OR REPLACE INTO secret_recipients
                    (secret_id, device_id, encrypted_dek)
                VALUES (?, ?, ?)
                """,
                [
                    (r.secret_id, r.device_id, r.encrypted_dek)
                    for r in recipients
                ],
            )

    def remove(self, secret_id: str, device_id: str) -> None:
        """Remove the DEK entry for one specific (secret, device) pair."""
        with self._conn:
            self._conn.execute(
                """
                DELETE FROM secret_recipients
                 WHERE secret_id = ? AND device_id = ?
                """,
                (secret_id, device_id),
            )

    def remove_all_for_secret(self, secret_id: str) -> None:
        """Remove every recipient row for a given secret.

        Use this before re-wrapping the DEK for a new set of devices.
        The cascade rule on ``secrets`` handles this automatically when the
        secret row itself is deleted; this method is for explicit re-key flows.
        """
        with self._conn:
            self._conn.execute(
                "DELETE FROM secret_recipients WHERE secret_id = ?",
                (secret_id,),
            )

    def remove_all_for_device(self, device_id: str) -> None:
        """Remove every recipient row for a revoked device.

        After calling this the device can no longer decrypt any secrets even
        if it still holds old ciphertext, because it can no longer obtain a DEK.
        """
        with self._conn:
            self._conn.execute(
                "DELETE FROM secret_recipients WHERE device_id = ?",
                (device_id,),
            )

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get(self, secret_id: str, device_id: str) -> SecretRecipient | None:
        """Return the single recipient record for a (secret, device) pair, or *None*."""
        row = self._conn.execute(
            """
            SELECT * FROM secret_recipients
             WHERE secret_id = ? AND device_id = ?
            """,
            (secret_id, device_id),
        ).fetchone()
        return _row_to_model(row) if row else None

    def list_by_secret(self, secret_id: str) -> list[SecretRecipient]:
        """Return all devices that hold a wrapped DEK for *secret_id*."""
        rows = self._conn.execute(
            "SELECT * FROM secret_recipients WHERE secret_id = ?",
            (secret_id,),
        ).fetchall()
        return [_row_to_model(r) for r in rows]

    def list_by_device(self, device_id: str) -> list[SecretRecipient]:
        """Return all (secret, wrapped-DEK) pairs accessible to *device_id*.

        This is the hot path during decryption; it uses the index
        ``idx_recipients_device`` created by the schema migration.
        """
        rows = self._conn.execute(
            "SELECT * FROM secret_recipients WHERE device_id = ?",
            (device_id,),
        ).fetchall()
        return [_row_to_model(r) for r in rows]

    def exists(self, secret_id: str, device_id: str) -> bool:
        """Return *True* when the given (secret, device) pair has a stored DEK."""
        row = self._conn.execute(
            """
            SELECT 1 FROM secret_recipients
             WHERE secret_id = ? AND device_id = ?
            """,
            (secret_id, device_id),
        ).fetchone()
        return row is not None


# ---------------------------------------------------------------------------
# Mapping helper
# ---------------------------------------------------------------------------

def _row_to_model(row: sqlite3.Row) -> SecretRecipient:
    dek = row["encrypted_dek"]
    if isinstance(dek, str):
        dek = dek.encode()
    return SecretRecipient(
        secret_id=row["secret_id"],
        device_id=row["device_id"],
        encrypted_dek=dek,
    )
