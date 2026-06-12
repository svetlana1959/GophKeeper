"""Integration test for GophStore facade."""

import sys, os, unittest, tempfile, pathlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from store.models import LocalDevice, Secret, SecretRecipient, TrustedDevice
from store.store import GophStore


class TestGophStore(unittest.TestCase):
    def setUp(self):
        self.store = GophStore(":memory:")
        self.store.open()

    def tearDown(self):
        self.store.close()

    def test_raises_when_not_open(self):
        s = GophStore(":memory:")
        with self.assertRaises(RuntimeError):
            _ = s.trusted_devices

    def test_context_manager(self):
        with GophStore(":memory:") as s:
            self.assertIsNotNone(s.trusted_devices)

    def test_full_lifecycle(self):
        store = self.store
        # Register local device
        store.trusted_devices.add(TrustedDevice(id="local", device_name="laptop", public_key="age1pub"))
        store.local_device.save(LocalDevice(device_id="local", private_key_encrypted=b"enc-priv"))
        self.assertTrue(store.local_device.exists())

        # Peer device
        store.trusted_devices.add(TrustedDevice(id="peer", device_name="phone", public_key="age1peer"))

        # Create secret
        store.secrets.add(Secret(id="s1", encrypted_payload=b"blob", nonce=b"nonce00000000001", folder_id="work"))

        # Share DEKs
        store.secret_recipients.add_many([
            SecretRecipient("s1", "local", b"dek-local"),
            SecretRecipient("s1", "peer",  b"dek-peer"),
        ])

        # Retrieve DEK
        self.assertEqual(store.secret_recipients.get("s1", "local").encrypted_dek, b"dek-local")

        # Soft-delete
        store.secrets.soft_delete("s1")
        self.assertTrue(store.secrets.get("s1").is_deleted)
        self.assertEqual(store.secrets.list_active(), [])

        # Hard-delete cascades to recipients
        store.secrets.hard_delete("s1")
        self.assertIsNone(store.secret_recipients.get("s1", "local"))

    def test_revoke_device_removes_deks(self):
        store = self.store
        store.trusted_devices.add(TrustedDevice(id="d1", device_name="laptop", public_key="age1d1"))
        store.secrets.add(Secret(id="s1", encrypted_payload=b"ct", nonce=b"nonce00000000001"))
        store.secret_recipients.add(SecretRecipient("s1", "d1", b"dek"))
        store.trusted_devices.deactivate("d1")
        store.secret_recipients.remove_all_for_device("d1")
        self.assertEqual(store.secret_recipients.list_by_device("d1"), [])

    def test_file_based_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = pathlib.Path(tmp) / ".goph" / "secrets.db"
            with GophStore(db_path) as s:
                s.trusted_devices.add(TrustedDevice(id="x", device_name="x", public_key="age1x"))
            self.assertTrue(db_path.exists())


if __name__ == "__main__":
    unittest.main()
