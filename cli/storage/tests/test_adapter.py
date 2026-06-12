"""Tests for store.adapter.db (DBAdapter)."""

import sqlite3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from store.adapter.db import DBAdapter, _SCHEMA_SQL


EXPECTED_TABLES = {"trusted_devices", "local_device", "secrets", "secret_recipients"}
EXPECTED_INDEX = "idx_recipients_device"


def _table_names(conn):
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {r[0] for r in rows}


def _index_names(conn):
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
    return {r[0] for r in rows}


class TestDBAdapterOpen(unittest.TestCase):
    def test_creates_all_tables(self):
        with DBAdapter(":memory:") as db:
            self.assertTrue(EXPECTED_TABLES.issubset(_table_names(db.connection)))

    def test_creates_recipient_index(self):
        with DBAdapter(":memory:") as db:
            self.assertIn(EXPECTED_INDEX, _index_names(db.connection))

    def test_foreign_keys_enabled(self):
        with DBAdapter(":memory:") as db:
            row = db.connection.execute("PRAGMA foreign_keys").fetchone()
        self.assertEqual(row[0], 1)

    def test_wal_mode_enabled(self):
        with DBAdapter(":memory:") as db:
            row = db.connection.execute("PRAGMA journal_mode").fetchone()
        self.assertIn(row[0], ("wal", "memory"))

    def test_open_is_idempotent(self):
        db = DBAdapter(":memory:")
        db.open()
        conn_first = db.connection
        db.open()
        self.assertIs(db.connection, conn_first)
        db.close()

    def test_connection_raises_when_closed(self):
        db = DBAdapter(":memory:")
        with self.assertRaises(RuntimeError):
            _ = db.connection

    def test_close_then_reopen(self):
        db = DBAdapter(":memory:")
        db.open()
        db.close()
        db.open()
        self.assertTrue(EXPECTED_TABLES.issubset(_table_names(db.connection)))
        db.close()

    def test_migration_is_idempotent(self):
        with DBAdapter(":memory:") as db:
            db.connection.executescript(_SCHEMA_SQL)  # second run — no error

    def test_file_db_creates_directory(self):
        import tempfile, pathlib
        with tempfile.TemporaryDirectory() as tmp:
            db_path = pathlib.Path(tmp) / "subdir" / ".goph" / "secrets.db"
            with DBAdapter(db_path) as db:
                tables = _table_names(db.connection)
            self.assertTrue(db_path.exists())
            self.assertTrue(EXPECTED_TABLES.issubset(tables))


if __name__ == "__main__":
    unittest.main()
