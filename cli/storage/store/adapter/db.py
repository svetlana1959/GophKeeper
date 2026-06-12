"""
store.adapter.db
~~~~~~~~~~~~~~~~

SQLite adapter — owns the database lifecycle and schema.

Responsibilities
----------------
* Creates the ``.goph`` directory + DB file when missing.
* Opens the connection with WAL mode and foreign-key enforcement.
* Runs idempotent schema migrations on first open (CREATE TABLE IF NOT EXISTS).
* Exposes a single :class:`DBAdapter` whose :pymeth:`connection` property the
  repositories use.  No business logic lives here.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# DDL — all migrations are idempotent (IF NOT EXISTS / IF NOT EXISTS INDEX)
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """\
-- 1. Base table for all devices (local and remote)
CREATE TABLE IF NOT EXISTS trusted_devices (
    id          TEXT PRIMARY KEY,
    device_name TEXT    NOT NULL,
    public_key  TEXT    NOT NULL,
    is_active   INTEGER DEFAULT 1,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. Extension table for the CURRENT local device only (1:1 relationship)
CREATE TABLE IF NOT EXISTS local_device (
    device_id             TEXT PRIMARY KEY,
    private_key_encrypted TEXT NOT NULL,
    created_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES trusted_devices(id) ON DELETE CASCADE
);

-- 3. Atomic secrets — ciphertext only, no plaintext columns
CREATE TABLE IF NOT EXISTS secrets (
    id                TEXT    PRIMARY KEY,
    folder_id         TEXT    DEFAULT '',
    encrypted_payload BLOB    NOT NULL,
    nonce             BLOB    NOT NULL,
    version           INTEGER DEFAULT 1,
    is_deleted        INTEGER DEFAULT 0,
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 4. Junction table: one wrapped DEK copy per (secret, device) pair
CREATE TABLE IF NOT EXISTS secret_recipients (
    secret_id     TEXT NOT NULL,
    device_id     TEXT NOT NULL,
    encrypted_dek BLOB NOT NULL,
    PRIMARY KEY (secret_id, device_id),
    FOREIGN KEY (secret_id) REFERENCES secrets(id)        ON DELETE CASCADE,
    FOREIGN KEY (device_id) REFERENCES trusted_devices(id) ON DELETE CASCADE
);

-- Fast lookup during decryption: find all secrets a device can decrypt
CREATE INDEX IF NOT EXISTS idx_recipients_device
    ON secret_recipients(device_id);
"""


class DBAdapter:
    """Manages the SQLite connection for the local encrypted store.

    Parameters
    ----------
    db_path:
        Filesystem path to the SQLite database file **or** the special
        string ``":memory:"`` for an in-memory database (tests).
    dir_mode:
        Unix permission bits for the ``.goph`` parent directory when it
        must be created.  Defaults to ``0o700`` (owner-only).
    """

    def __init__(
        self,
        db_path: str | os.PathLike[str] = ":memory:",
        dir_mode: int = 0o700,
    ) -> None:
        self._db_path = str(db_path)
        self._dir_mode = dir_mode
        self._conn: Optional[sqlite3.Connection] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def open(self) -> None:
        """Open (or create) the database and run schema migrations.

        Safe to call multiple times; subsequent calls are no-ops when the
        connection is already open.
        """
        if self._conn is not None:
            return

        self._ensure_directory()
        self._conn = sqlite3.connect(
            self._db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            check_same_thread=False,
        )
        self._configure(self._conn)
        self._migrate(self._conn)

        if self._db_path != ":memory:":
            # Restrict file permissions so the private key at rest is
            # readable by the owner only.
            os.chmod(self._db_path, 0o600)

    def close(self) -> None:
        """Close the underlying connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @property
    def connection(self) -> sqlite3.Connection:
        """Return the open :class:`sqlite3.Connection`.

        Raises
        ------
        RuntimeError
            If :pymeth:`open` has not been called yet.
        """
        if self._conn is None:
            raise RuntimeError(
                "DBAdapter is not open. Call open() before accessing the connection."
            )
        return self._conn

    # Context-manager support so callers can use ``with DBAdapter(...) as db:``
    def __enter__(self) -> "DBAdapter":
        self.open()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ensure_directory(self) -> None:
        """Create the parent directory (e.g. ``~/.goph``) when missing."""
        if self._db_path == ":memory:":
            return
        parent = Path(self._db_path).parent
        if not parent.exists():
            parent.mkdir(parents=True, mode=self._dir_mode, exist_ok=True)

    @staticmethod
    def _configure(conn: sqlite3.Connection) -> None:
        """Apply per-connection SQLite pragmas."""
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous  = NORMAL")
        # Return rows as sqlite3.Row so columns are accessible by name
        conn.row_factory = sqlite3.Row

    @staticmethod
    def _migrate(conn: sqlite3.Connection) -> None:
        """Run the full schema in one transaction (idempotent)."""
        with conn:
            conn.executescript(_SCHEMA_SQL)
