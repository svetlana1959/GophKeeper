"""Tests for LocalDeviceRepository."""

import sqlite3, sys, os, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from store.adapter.db import DBAdapter
from store.models import LocalDevice, TrustedDevice
from store.repository.local_device import LocalDeviceRepository
from store.repository.trusted_devices import TrustedDeviceRepository


def seed_trusted(dev_repo, device_id="dev-001"):
    dev_repo.add(TrustedDevice(id=device_id, device_name="test", public_key="age1pub"))
    return device_id


class TestLocalDevice(unittest.TestCase):
    def setUp(self):
        self.adapter = DBAdapter(":memory:")
        self.adapter.open()
        self.repo = LocalDeviceRepository(self.adapter.connection)
        self.dev_repo = TrustedDeviceRepository(self.adapter.connection)

    def tearDown(self):
        self.adapter.close()

    def test_get_none_when_uninitialised(self):
        self.assertIsNone(self.repo.get())

    def test_exists_false_when_uninitialised(self):
        self.assertFalse(self.repo.exists())

    def test_save_then_get(self):
        seed_trusted(self.dev_repo)
        self.repo.save(LocalDevice(device_id="dev-001", private_key_encrypted=b"blob"))
        r = self.repo.get()
        self.assertIsNotNone(r)
        self.assertEqual(r.private_key_encrypted, b"blob")

    def test_exists_true_after_save(self):
        seed_trusted(self.dev_repo)
        self.repo.save(LocalDevice(device_id="dev-001", private_key_encrypted=b"blob"))
        self.assertTrue(self.repo.exists())

    def test_save_replaces_existing(self):
        seed_trusted(self.dev_repo)
        self.repo.save(LocalDevice(device_id="dev-001", private_key_encrypted=b"old"))
        self.repo.save(LocalDevice(device_id="dev-001", private_key_encrypted=b"new"))
        self.assertEqual(self.repo.get().private_key_encrypted, b"new")

    def test_get_by_id(self):
        seed_trusted(self.dev_repo)
        self.repo.save(LocalDevice(device_id="dev-001", private_key_encrypted=b"blob"))
        r = self.repo.get_by_id("dev-001")
        self.assertIsNotNone(r)

    def test_get_by_id_unknown_returns_none(self):
        self.assertIsNone(self.repo.get_by_id("ghost"))

    def test_update_private_key(self):
        seed_trusted(self.dev_repo)
        self.repo.save(LocalDevice(device_id="dev-001", private_key_encrypted=b"old"))
        self.repo.update_private_key("dev-001", b"rotated")
        self.assertEqual(self.repo.get().private_key_encrypted, b"rotated")

    def test_update_nonexistent_noop(self):
        self.repo.update_private_key("ghost", b"key")

    def test_delete(self):
        seed_trusted(self.dev_repo)
        self.repo.save(LocalDevice(device_id="dev-001", private_key_encrypted=b"blob"))
        self.repo.delete("dev-001")
        self.assertIsNone(self.repo.get())

    def test_fk_requires_trusted_device(self):
        with self.assertRaises((sqlite3.IntegrityError, sqlite3.OperationalError)):
            self.repo.save(LocalDevice(device_id="orphan", private_key_encrypted=b"k"))


if __name__ == "__main__":
    unittest.main()
