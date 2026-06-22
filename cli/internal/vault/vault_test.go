package vault

import (
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/svetlana1959/GophKeeper/cli/internal/domain"
)

func openTestAdapter(t *testing.T, path string) *Adapter {
	t.Helper()
	adapter, err := Open(path)
	if err != nil {
		t.Fatalf("failed to open vault adapter: %v", err)
	}
	return adapter
}

func TestAdapterCreatesDatabaseAndSchema(t *testing.T) {
	tmp := t.TempDir()
	path := filepath.Join(tmp, "secrets.db")
	adapter := openTestAdapter(t, path)
	defer adapter.Close()

	if _, err := os.Stat(path); err != nil {
		t.Fatalf("expected database file to exist: %v", err)
	}
}

func TestTrustedDeviceRepoCRUD(t *testing.T) {
	adapter := openTestAdapter(t, ":memory:")
	defer adapter.Close()

	repo := adapter.TrustedDeviceRepo()
	device := &domain.TrustedDevice{
		ID:         "device-1",
		DeviceName: "laptop",
		PublicKey:  "age1publickey",
		IsActive:   true,
	}

	if err := repo.Create(device); err != nil {
		t.Fatal(err)
	}

	fetched, err := repo.Get(device.ID)
	if err != nil {
		t.Fatal(err)
	}
	if fetched.DeviceName != device.DeviceName || fetched.PublicKey != device.PublicKey || !fetched.IsActive {
		t.Fatal("retrieved trusted device mismatch")
	}

	devices, err := repo.List(true)
	if err != nil {
		t.Fatal(err)
	}
	if len(devices) != 1 {
		t.Fatalf("expected 1 active trusted device, got %d", len(devices))
	}

	device.DeviceName = "office-laptop"
	device.IsActive = false
	if err := repo.Update(device); err != nil {
		t.Fatal(err)
	}

	fetched, err = repo.Get(device.ID)
	if err != nil {
		t.Fatal(err)
	}
	if fetched.DeviceName != "office-laptop" || fetched.IsActive {
		t.Fatal("trusted device update did not persist")
	}

	if err := repo.Activate(device.ID); err != nil {
		t.Fatal(err)
	}
	if err := repo.Deactivate(device.ID); err != nil {
		t.Fatal(err)
	}
}

func TestLocalDeviceRepoStoreGetDelete(t *testing.T) {
	adapter := openTestAdapter(t, ":memory:")
	defer adapter.Close()

	repo := adapter.LocalDeviceRepo()
	local := &domain.LocalDevice{
		DeviceID:            "device-1",
		PrivateKeyEncrypted: []byte("encrypted-key"),
	}

	if err := repo.Store(local); err != nil {
		t.Fatal(err)
	}

	fetched, err := repo.Get()
	if err != nil {
		t.Fatal(err)
	}
	if fetched.DeviceID != local.DeviceID || string(fetched.PrivateKeyEncrypted) != string(local.PrivateKeyEncrypted) {
		t.Fatal("stored local device mismatch")
	}

	if err := repo.Delete(); err != nil {
		t.Fatal(err)
	}
	if _, err := repo.Get(); err == nil {
		t.Fatal("expected error after deleting local device")
	}
}

func TestSecretRepoCRUD(t *testing.T) {
	adapter := openTestAdapter(t, ":memory:")
	defer adapter.Close()

	repo := adapter.SecretRepo()
	secret := &domain.Secret{
		ID:        "secret-1",
		Name:      "personal-note",
		FolderID:  "personal",
		Payload:   []byte("ciphertext"),
		Nonce:     []byte("nonce123456"),
		Version:   1,
		Deleted:   false,
		CreatedAt: time.Now().UTC(),
	}

	if err := repo.Save(secret); err != nil {
		t.Fatal(err)
	}

	fetched, err := repo.Get(secret.ID)
	if err != nil {
		t.Fatal(err)
	}
	if fetched.Name != secret.Name || fetched.FolderID != secret.FolderID || string(fetched.Payload) != string(secret.Payload) {
		t.Fatal("retrieved secret mismatch")
	}

	found, err := repo.FindByName(secret.Name)
	if err != nil {
		t.Fatal(err)
	}
	if found.ID != secret.ID {
		t.Fatal("FindByName returned wrong secret")
	}

	secret.Version = 2
	secret.Deleted = true
	if err := repo.Save(secret); err != nil {
		t.Fatal(err)
	}

	active, err := repo.List(false)
	if err != nil {
		t.Fatal(err)
	}
	if len(active) != 0 {
		t.Fatal("expected no active secrets after soft delete")
	}

	all, err := repo.List(true)
	if err != nil {
		t.Fatal(err)
	}
	if len(all) != 1 {
		t.Fatal("expected one secret when includeDeleted=true")
	}

	if err := repo.Purge(secret.ID); err != nil {
		t.Fatal(err)
	}
	if _, err := repo.Get(secret.ID); err == nil {
		t.Fatal("expected secret not found after purge")
	}
}

func TestSecretRecipientRepoAddListRemove(t *testing.T) {
	adapter := openTestAdapter(t, ":memory:")
	defer adapter.Close()

	secretRepo := adapter.SecretRepo()
	deviceRepo := adapter.TrustedDeviceRepo()
	recipientRepo := adapter.SecretRecipientRepo()

	device := &domain.TrustedDevice{
		ID:         "device-1",
		DeviceName: "laptop",
		PublicKey:  "age1pub",
	}
	if err := deviceRepo.Create(device); err != nil {
		t.Fatal(err)
	}

	secret := &domain.Secret{
		ID:        "secret-1",
		Name:      "personal-note",
		FolderID:  "personal",
		Payload:   []byte("ciphertext"),
		Nonce:     []byte("nonce123456"),
		Version:   1,
	}
	if err := secretRepo.Save(secret); err != nil {
		t.Fatal(err)
	}

	recipient := &domain.SecretRecipient{
		SecretID:     secret.ID,
		DeviceID:     device.ID,
		EncryptedDEK: []byte("wrapped-dek"),
	}
	if err := recipientRepo.Add(recipient); err != nil {
		t.Fatal(err)
	}

	list, err := recipientRepo.List(secret.ID)
	if err != nil {
		t.Fatal(err)
	}
	if len(list) != 1 || string(list[0].EncryptedDEK) != string(recipient.EncryptedDEK) {
		t.Fatal("secret recipient list returned unexpected data")
	}

	found, err := recipientRepo.Get(secret.ID, device.ID)
	if err != nil {
		t.Fatal(err)
	}
	if string(found.EncryptedDEK) != string(recipient.EncryptedDEK) {
		t.Fatal("secret recipient get returned unexpected data")
	}

	if err := recipientRepo.Remove(secret.ID, device.ID); err != nil {
		t.Fatal(err)
	}
	if _, err := recipientRepo.Get(secret.ID, device.ID); err == nil {
		t.Fatal("expected secret recipient not found after removal")
	}
}
