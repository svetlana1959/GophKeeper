"""Tests for SecretRecipientRepository."""

import sys, os, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from store.adapter.db import DBAdapter
from store.models import Secret, SecretRecipient, TrustedDevice
from store.repository.secret_recipients import SecretRecipientRepository
from store.repository.secrets import SecretRepository
from store.repository.trusted_devices import TrustedDeviceRepository


def seed_device(dev_repo, device_id, name="dev"):
    dev_repo.add(TrustedDevice(id=device_id, device_name=name, public_key=f"age1{device_id}"))

def seed_secret(sec_repo, secret_id):
    sec_repo.add(Secret(id=secret_id, encrypted_payload=b"ct", nonce=b"nonce00000000001"))

def make_rec(sid, did, dek=b"dek"):
    return SecretRecipient(secret_id=sid, device_id=did, encrypted_dek=dek)


class TestSecretRecipients(unittest.TestCase):
    def setUp(self):
        self.adapter = DBAdapter(":memory:")
        self.adapter.open()
        conn = self.adapter.connection
        self.dev_repo = TrustedDeviceRepository(conn)
        self.sec_repo = SecretRepository(conn)
        self.repo = SecretRecipientRepository(conn)

    def tearDown(self):
        self.adapter.close()

    # add / get
    def test_add_then_get(self):
        seed_device(self.dev_repo, "d1")
        seed_secret(self.sec_repo, "s1")
        self.repo.add(make_rec("s1", "d1", b"mydek"))
        r = self.repo.get("s1", "d1")
        self.assertIsNotNone(r)
        self.assertEqual(r.encrypted_dek, b"mydek")

    def test_get_unknown_returns_none(self):
        self.assertIsNone(self.repo.get("x", "y"))

    def test_exists(self):
        seed_device(self.dev_repo, "d1")
        seed_secret(self.sec_repo, "s1")
        self.repo.add(make_rec("s1", "d1"))
        self.assertTrue(self.repo.exists("s1", "d1"))
        self.assertFalse(self.repo.exists("s1", "d9"))

    def test_add_replaces_dek_on_rekey(self):
        seed_device(self.dev_repo, "d1")
        seed_secret(self.sec_repo, "s1")
        self.repo.add(make_rec("s1", "d1", b"old"))
        self.repo.add(make_rec("s1", "d1", b"new"))
        self.assertEqual(self.repo.get("s1", "d1").encrypted_dek, b"new")

    # add_many
    def test_add_many(self):
        for i in range(1, 4):
            seed_device(self.dev_repo, f"d{i}")
        seed_secret(self.sec_repo, "s1")
        self.repo.add_many([make_rec("s1", f"d{i}") for i in range(1, 4)])
        self.assertEqual(len(self.repo.list_by_secret("s1")), 3)

    def test_add_many_empty_noop(self):
        self.repo.add_many([])

    # remove
    def test_remove_single(self):
        seed_device(self.dev_repo, "d1")
        seed_device(self.dev_repo, "d2")
        seed_secret(self.sec_repo, "s1")
        self.repo.add(make_rec("s1", "d1"))
        self.repo.add(make_rec("s1", "d2"))
        self.repo.remove("s1", "d1")
        self.assertIsNone(self.repo.get("s1", "d1"))
        self.assertIsNotNone(self.repo.get("s1", "d2"))

    def test_remove_nonexistent_noop(self):
        self.repo.remove("x", "y")

    def test_remove_all_for_secret(self):
        seed_device(self.dev_repo, "d1")
        seed_device(self.dev_repo, "d2")
        seed_secret(self.sec_repo, "s1")
        self.repo.add(make_rec("s1", "d1"))
        self.repo.add(make_rec("s1", "d2"))
        self.repo.remove_all_for_secret("s1")
        self.assertEqual(self.repo.list_by_secret("s1"), [])

    def test_remove_all_for_device(self):
        seed_device(self.dev_repo, "d1")
        seed_secret(self.sec_repo, "s1")
        seed_secret(self.sec_repo, "s2")
        self.repo.add(make_rec("s1", "d1"))
        self.repo.add(make_rec("s2", "d1"))
        self.repo.remove_all_for_device("d1")
        self.assertEqual(self.repo.list_by_device("d1"), [])

    # listing
    def test_list_by_secret(self):
        seed_device(self.dev_repo, "d1")
        seed_device(self.dev_repo, "d2")
        seed_secret(self.sec_repo, "s1")
        self.repo.add(make_rec("s1", "d1"))
        self.repo.add(make_rec("s1", "d2"))
        self.assertEqual({r.device_id for r in self.repo.list_by_secret("s1")}, {"d1", "d2"})

    def test_list_by_device(self):
        seed_device(self.dev_repo, "d1")
        seed_secret(self.sec_repo, "s1")
        seed_secret(self.sec_repo, "s2")
        self.repo.add(make_rec("s1", "d1"))
        self.repo.add(make_rec("s2", "d1"))
        self.assertEqual({r.secret_id for r in self.repo.list_by_device("d1")}, {"s1", "s2"})

    def test_list_empty(self):
        self.assertEqual(self.repo.list_by_secret("ghost"), [])
        self.assertEqual(self.repo.list_by_device("ghost"), [])

    # cascade
    def test_cascade_secret_delete(self):
        seed_device(self.dev_repo, "d1")
        seed_secret(self.sec_repo, "s1")
        self.repo.add(make_rec("s1", "d1"))
        self.sec_repo.hard_delete("s1")
        self.assertIsNone(self.repo.get("s1", "d1"))

    def test_cascade_device_delete(self):
        seed_device(self.dev_repo, "d1")
        seed_secret(self.sec_repo, "s1")
        self.repo.add(make_rec("s1", "d1"))
        self.dev_repo.delete("d1")
        self.assertIsNone(self.repo.get("s1", "d1"))


if __name__ == "__main__":
    unittest.main()
