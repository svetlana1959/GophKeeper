"""Tests for SecretRepository."""

import sqlite3, sys, os, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from store.adapter.db import DBAdapter
from store.models import Secret
from store.repository.secrets import SecretRepository


def make_secret(id="s1", payload=b"ct", nonce=b"nonce00000000001",
                folder_id="", version=1, is_deleted=False):
    return Secret(id=id, encrypted_payload=payload, nonce=nonce,
                  folder_id=folder_id, version=version, is_deleted=is_deleted)


class TestSecrets(unittest.TestCase):
    def setUp(self):
        self.adapter = DBAdapter(":memory:")
        self.adapter.open()
        self.repo = SecretRepository(self.adapter.connection)

    def tearDown(self):
        self.adapter.close()

    # add / get
    def test_add_then_get(self):
        self.repo.add(make_secret(id="s1", payload=b"enc", nonce=b"nonce00000000001"))
        s = self.repo.get("s1")
        self.assertIsNotNone(s)
        self.assertEqual(s.encrypted_payload, b"enc")
        self.assertEqual(s.nonce, b"nonce00000000001")
        self.assertFalse(s.is_deleted)

    def test_get_unknown_returns_none(self):
        self.assertIsNone(self.repo.get("ghost"))

    def test_add_duplicate_raises(self):
        self.repo.add(make_secret())
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.add(make_secret())

    def test_exists(self):
        self.repo.add(make_secret(id="s1"))
        self.assertTrue(self.repo.exists("s1"))
        self.assertFalse(self.repo.exists("ghost"))

    # update
    def test_update_payload_and_nonce(self):
        self.repo.add(make_secret(id="s1", payload=b"old", nonce=b"nonce00000000001", version=1))
        s = self.repo.get("s1")
        s.encrypted_payload = b"new"
        s.nonce = b"nonce00000000002"
        s.version = 2
        self.repo.update(s)
        r = self.repo.get("s1")
        self.assertEqual(r.encrypted_payload, b"new")
        self.assertEqual(r.version, 2)

    def test_update_deleted_is_noop(self):
        self.repo.add(make_secret(id="s1", payload=b"orig"))
        self.repo.soft_delete("s1")
        s = self.repo.get("s1")
        s.encrypted_payload = b"should-not-persist"
        self.repo.update(s)
        self.assertEqual(self.repo.get("s1").encrypted_payload, b"orig")

    # soft_delete / hard_delete
    def test_soft_delete_sets_tombstone(self):
        self.repo.add(make_secret(id="s1"))
        self.repo.soft_delete("s1")
        self.assertTrue(self.repo.get("s1").is_deleted)

    def test_soft_deleted_excluded_from_list_active(self):
        self.repo.add(make_secret(id="s1"))
        self.repo.add(make_secret(id="s2"))
        self.repo.soft_delete("s1")
        ids = {s.id for s in self.repo.list_active()}
        self.assertNotIn("s1", ids)
        self.assertIn("s2", ids)

    def test_soft_deleted_in_list_all(self):
        self.repo.add(make_secret(id="s1"))
        self.repo.soft_delete("s1")
        self.assertTrue(any(s.id == "s1" for s in self.repo.list_all()))

    def test_hard_delete(self):
        self.repo.add(make_secret(id="s1"))
        self.repo.hard_delete("s1")
        self.assertIsNone(self.repo.get("s1"))

    def test_soft_delete_nonexistent_noop(self):
        self.repo.soft_delete("ghost")

    def test_hard_delete_nonexistent_noop(self):
        self.repo.hard_delete("ghost")

    # listing
    def test_list_active_by_folder(self):
        self.repo.add(make_secret(id="s1", folder_id="work"))
        self.repo.add(make_secret(id="s2", folder_id="personal"))
        self.repo.add(make_secret(id="s3", folder_id="work"))
        ids = {s.id for s in self.repo.list_active(folder_id="work")}
        self.assertEqual(ids, {"s1", "s3"})

    def test_list_deleted(self):
        self.repo.add(make_secret(id="s1"))
        self.repo.add(make_secret(id="s2"))
        self.repo.soft_delete("s1")
        deleted = self.repo.list_deleted()
        self.assertEqual(len(deleted), 1)
        self.assertEqual(deleted[0].id, "s1")

    def test_list_all_includes_tombstones(self):
        self.repo.add(make_secret(id="s1"))
        self.repo.add(make_secret(id="s2"))
        self.repo.soft_delete("s2")
        self.assertEqual(len(self.repo.list_all()), 2)


if __name__ == "__main__":
    unittest.main()
