"""
store.repository.secrets
~~~~~~~~~~~~~~~~~~~~~~~~~~

Repository for the ``secrets`` table.

Supported operations
--------------------
* ``add``          — insert a new secret (ciphertext + nonce only).
* ``get``          — fetch one by UUID.
* ``list_active``  — all non-deleted secrets, optionally filtered by folder.
* ``list_all``     — include tombstones (needed during sync).
* ``update``       — replace payload/nonce and bump version.
* ``soft_delete``  — set is_deleted = 1 (tombstone).
* ``hard_delete``  — remove the row entirely (cascades to secret_recipients).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional

from store.models import Secret


class SecretRepository:
    """CRUD + soft-delete for the ``secrets`` table.

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

    def add(self, secret: Secret) -> None:
        """Insert a new secret row.

        Both ``encrypted_payload`` and ``nonce`` must already be ciphertext —
        this method never touches plaintext.

        Raises
        ------
        sqlite3.IntegrityError
            If a secret with the same ``id`` already exists.
        """
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO secrets
                    (id, folder_id, encrypted_payload, nonce,
                     version, is_deleted, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    secret.id,
                    secret.folder_id,
                    secret.encrypted_payload,
                    secret.nonce,
                    secret.version,
                    int(secret.is_deleted),
                    secret.created_at.isoformat(),
                    secret.updated_at.isoformat(),
                ),
            )

    def update(self, secret: Secret) -> None:
        """Replace the encrypted payload, nonce, folder and bump the version.

        ``updated_at`` is refreshed to the current UTC time.

        Only updates non-deleted secrets; use :pymeth:`soft_delete` separately
        if you also need to tombstone the row.
        """
        with self._conn:
            self._conn.execute(
                """
                UPDATE secrets
                   SET folder_id         = ?,
                       encrypted_payload = ?,
                       nonce             = ?,
                       version           = ?,
                       updated_at        = ?
                 WHERE id = ?
                   AND is_deleted = 0
                """,
                (
                    secret.folder_id,
                    secret.encrypted_payload,
                    secret.nonce,
                    secret.version,
                    datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                    secret.id,
                ),
            )

    def soft_delete(self, secret_id: str) -> None:
        """Mark a secret as deleted (tombstone).  The row is kept for sync purposes."""
        with self._conn:
            self._conn.execute(
                """
                UPDATE secrets
                   SET is_deleted = 1, updated_at = ?
                 WHERE id = ?
                """,
                (datetime.now(timezone.utc).replace(tzinfo=None).isoformat(), secret_id),
            )

    def hard_delete(self, secret_id: str) -> None:
        """Permanently remove a secret row (cascades to secret_recipients)."""
        with self._conn:
            self._conn.execute(
                "DELETE FROM secrets WHERE id = ?",
                (secret_id,),
            )

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get(self, secret_id: str) -> Optional[Secret]:
        """Return a single secret by primary key (including deleted ones), or *None*."""
        row = self._conn.execute(
            "SELECT * FROM secrets WHERE id = ?",
            (secret_id,),
        ).fetchone()
        return _row_to_model(row) if row else None

    def list_active(self, folder_id: Optional[str] = None) -> list[Secret]:
        """Return all non-deleted secrets, newest first.

        Parameters
        ----------
        folder_id:
            When given, restricts results to that folder.
        """
        if folder_id is not None:
            rows = self._conn.execute(
                """
                SELECT * FROM secrets
                 WHERE is_deleted = 0 AND folder_id = ?
                 ORDER BY updated_at DESC
                """,
                (folder_id,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT * FROM secrets
                 WHERE is_deleted = 0
                 ORDER BY updated_at DESC
                """
            ).fetchall()
        return [_row_to_model(r) for r in rows]

    def list_all(self) -> list[Secret]:
        """Return every secret row, including tombstones (used during sync)."""
        rows = self._conn.execute(
            "SELECT * FROM secrets ORDER BY updated_at DESC"
        ).fetchall()
        return [_row_to_model(r) for r in rows]

    def list_deleted(self) -> list[Secret]:
        """Return only tombstoned secrets."""
        rows = self._conn.execute(
            "SELECT * FROM secrets WHERE is_deleted = 1 ORDER BY updated_at DESC"
        ).fetchall()
        return [_row_to_model(r) for r in rows]

    def exists(self, secret_id: str) -> bool:
        """Return *True* when a secret with the given id exists (even if deleted)."""
        row = self._conn.execute(
            "SELECT 1 FROM secrets WHERE id = ?",
            (secret_id,),
        ).fetchone()
        return row is not None


# ---------------------------------------------------------------------------
# Mapping helper
# ---------------------------------------------------------------------------

def _row_to_model(row: sqlite3.Row) -> Secret:
    payload = row["encrypted_payload"]
    nonce = row["nonce"]
    # BLOB columns come back as bytes; guard against TEXT-stored legacy rows.
    if isinstance(payload, str):
        payload = payload.encode()
    if isinstance(nonce, str):
        nonce = nonce.encode()
    return Secret(
        id=row["id"],
        folder_id=row["folder_id"] or "",
        encrypted_payload=payload,
        nonce=nonce,
        version=row["version"],
        is_deleted=bool(row["is_deleted"]),
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    return datetime.fromisoformat(value)
