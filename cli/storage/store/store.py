"""
store.store
~~~~~~~~~~~

Convenience facade that wires the :class:`DBAdapter` to all four repositories.

Usage
-----
::

    from store import GophStore

    with GophStore("~/.goph/secrets.db") as store:
        store.trusted_devices.add(device)
        store.secrets.add(secret)

Or without the context manager::

    store = GophStore("~/.goph/secrets.db")
    store.open()
    ...
    store.close()
"""

from __future__ import annotations

import os

from store.adapter.db import DBAdapter
from store.repository.trusted_devices import TrustedDeviceRepository
from store.repository.local_device import LocalDeviceRepository
from store.repository.secrets import SecretRepository
from store.repository.secret_recipients import SecretRecipientRepository


class GophStore:
    """High-level entry point for the local encrypted store.

    Instantiating this class does **not** open the database; call
    :pymeth:`open` (or use it as a context manager) first.

    Parameters
    ----------
    db_path:
        Path to the SQLite file, e.g. ``~/.goph/secrets.db``.
        Pass ``":memory:"`` for a fully in-memory database (tests / CI).
    """

    def __init__(self, db_path: str | os.PathLike[str] = ":memory:") -> None:
        self._adapter = DBAdapter(db_path)

        # Repositories are created eagerly but only usable after open()
        self._trusted_devices: TrustedDeviceRepository | None = None
        self._local_device: LocalDeviceRepository | None = None
        self._secrets: SecretRepository | None = None
        self._secret_recipients: SecretRecipientRepository | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def open(self) -> None:
        """Open the underlying SQLite connection and run schema migrations."""
        self._adapter.open()
        conn = self._adapter.connection
        self._trusted_devices = TrustedDeviceRepository(conn)
        self._local_device = LocalDeviceRepository(conn)
        self._secrets = SecretRepository(conn)
        self._secret_recipients = SecretRecipientRepository(conn)

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self._adapter.close()

    def __enter__(self) -> "GophStore":
        self.open()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Repository accessors
    # ------------------------------------------------------------------

    @property
    def trusted_devices(self) -> TrustedDeviceRepository:
        self._require_open()
        return self._trusted_devices  # type: ignore[return-value]

    @property
    def local_device(self) -> LocalDeviceRepository:
        self._require_open()
        return self._local_device  # type: ignore[return-value]

    @property
    def secrets(self) -> SecretRepository:
        self._require_open()
        return self._secrets  # type: ignore[return-value]

    @property
    def secret_recipients(self) -> SecretRecipientRepository:
        self._require_open()
        return self._secret_recipients  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _require_open(self) -> None:
        if self._trusted_devices is None:
            raise RuntimeError("GophStore is not open. Call open() first.")
