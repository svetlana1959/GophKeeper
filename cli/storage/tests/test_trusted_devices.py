"""Tests for TrustedDeviceRepository."""

import sqlite3, sys, os, unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from store.adapter.db import DBAdapter
from store.models import TrustedDevice
from store.repository.trusted_devices import TrustedDeviceRepository


def make_device(id="dev-001", name="laptop", pubkey="age1abc", is_active=True):
    return TrustedDevice(id=id, device_name=name, public_key=pubkey, is_active=is_active)


class TestTrustedDevices(unittest.TestCase):
    def setUp(self):
        self.adapter = DBAdapter(":memory:")
        self.adapter.open()
        self.repo = TrustedDeviceRepository(self.adapter.connection)

    def tearDown(self):
        self.adapter.close()

    # add / get
    def test_add_then_get(self):
        self.repo.add(make_device())
        r = self.repo.get("dev-001")
        self.assertIsNotNone(r)
        self.assertEqual(r.id, "dev-001")
        self.assertEqual(r.device_name, "laptop")
        self.assertTrue(r.is_active)

    def test_get_unknown_returns_none(self):
        self.assertIsNone(self.repo.get("nope"))

    def test_get_by_name(self):
        self.repo.add(make_device(id="d1", name="alice"))
        self.repo.add(make_device(id="d2", name="bob"))
        r = self.repo.get_by_name("bob")
        self.assertEqual(r.id, "d2")

    def test_get_by_name_unknown(self):
        self.assertIsNone(self.repo.get_by_name("ghost"))

    def test_add_duplicate_raises(self):
        self.repo.add(make_device())
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.add(make_device())

    # update
    def test_update_name(self):
        self.repo.add(make_device(id="d1"))
        d = self.repo.get("d1")
        d.device_name = "new-name"
        self.repo.update(d)
        self.assertEqual(self.repo.get("d1").device_name, "new-name")

    def test_update_public_key(self):
        self.repo.add(make_device(id="d1", pubkey="age1old"))
        d = self.repo.get("d1")
        d.public_key = "age1new"
        self.repo.update(d)
        self.assertEqual(self.repo.get("d1").public_key, "age1new")

    # delete
    def test_hard_delete(self):
        self.repo.add(make_device(id="d1"))
        self.repo.delete("d1")
        self.assertIsNone(self.repo.get("d1"))

    def test_delete_nonexistent_noop(self):
        self.repo.delete("ghost")

    # activate / deactivate
    def test_deactivate(self):
        self.repo.add(make_device(id="d1", is_active=True))
        self.repo.deactivate("d1")
        self.assertFalse(self.repo.get("d1").is_active)

    def test_activate(self):
        self.repo.add(make_device(id="d1", is_active=False))
        self.repo.activate("d1")
        self.assertTrue(self.repo.get("d1").is_active)

    # listing
    def test_list_all(self):
        self.repo.add(make_device(id="d1", is_active=True))
        self.repo.add(make_device(id="d2", is_active=False))
        self.assertEqual(len(self.repo.list_all()), 2)

    def test_list_active_excludes_revoked(self):
        self.repo.add(make_device(id="d1", is_active=True))
        self.repo.add(make_device(id="d2", is_active=False))
        active = self.repo.list_active()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].id, "d1")

    def test_list_empty(self):
        self.assertEqual(self.repo.list_all(), [])
        self.assertEqual(self.repo.list_active(), [])


if __name__ == "__main__":
    unittest.main()
