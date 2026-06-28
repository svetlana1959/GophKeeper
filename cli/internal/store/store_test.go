package store_test

import (
	"bytes"
	"context"
	"errors"
	"os"
	"path/filepath"
	"runtime"
	"testing"

	"github.com/svetlana1959/GophKeeper/cli/internal/store"
)

func openTemp(t *testing.T) *store.Adapter {
	t.Helper()
	dbPath := filepath.Join(t.TempDir(), ".goph", "secret.db")
	a, err := store.Open(context.Background(), dbPath)
	if err != nil {
		t.Fatalf("open: %v", err)
	}
	t.Cleanup(func() { _ = a.Close() })
	return a
}

func TestOpen_CreatesDirAndFilePerms(t *testing.T) {
	base := t.TempDir()
	dbPath := filepath.Join(base, ".goph", "secret.db")
	a, err := store.Open(context.Background(), dbPath)
	if err != nil {
		t.Fatalf("open: %v", err)
	}
	defer a.Close()

	if _, err := os.Stat(dbPath); err != nil {
		t.Fatalf("db file not created: %v", err)
	}
	if runtime.GOOS != "windows" { // Unix perms are meaningless on Windows
		info, _ := os.Stat(dbPath)
		if perm := info.Mode().Perm(); perm != 0o600 {
			t.Fatalf("db perms = %o, want 600", perm)
		}
	}
}

func TestDevices_CRUDAndActivation(t *testing.T) {
	ctx := context.Background()
	repo := openTemp(t).Devices()

	if err := repo.Save(ctx, store.TrustedDevice{
		ID: "dev-1", Name: "laptop-asus", PublicKey: "age1xyz", IsActive: true,
	}); err != nil {
		t.Fatalf("save: %v", err)
	}

	got, err := repo.GetByID(ctx, "dev-1")
	if err != nil {
		t.Fatalf("get: %v", err)
	}
	if got.Name != "laptop-asus" || !got.IsActive {
		t.Fatalf("unexpected: %+v", got)
	}

	if err := repo.Deactivate(ctx, "dev-1"); err != nil {
		t.Fatalf("deactivate: %v", err)
	}
	if got, _ = repo.GetByID(ctx, "dev-1"); got.IsActive {
		t.Fatal("expected inactive")
	}
	if err := repo.Activate(ctx, "dev-1"); err != nil {
		t.Fatalf("activate: %v", err)
	}

	// Upsert: saving same id updates fields.
	if err := repo.Save(ctx, store.TrustedDevice{
		ID: "dev-1", Name: "renamed", PublicKey: "age1xyz", IsActive: true,
	}); err != nil {
		t.Fatalf("upsert: %v", err)
	}
	if got, _ = repo.GetByID(ctx, "dev-1"); got.Name != "renamed" {
		t.Fatalf("upsert not applied: %+v", got)
	}

	list, err := repo.List(ctx)
	if err != nil || len(list) != 1 {
		t.Fatalf("list: %v len=%d", err, len(list))
	}

	if err := repo.Delete(ctx, "dev-1"); err != nil {
		t.Fatalf("delete: %v", err)
	}
	if _, err := repo.GetByID(ctx, "dev-1"); !errors.Is(err, store.ErrNotFound) {
		t.Fatalf("want ErrNotFound, got %v", err)
	}
	if err := repo.Deactivate(ctx, "ghost"); !errors.Is(err, store.ErrNotFound) {
		t.Fatalf("want ErrNotFound on missing, got %v", err)
	}
}

func TestLocalDevice_StoreRead_AndCascade(t *testing.T) {
	ctx := context.Background()
	a := openTemp(t)
	devices := a.Devices()
	local := a.LocalDevice()

	// FK: parent device must exist.
	if err := devices.Save(ctx, store.TrustedDevice{
		ID: "dev-1", Name: "me", PublicKey: "age1", IsActive: true,
	}); err != nil {
		t.Fatal(err)
	}

	blob := []byte{0x00, 0x01, 0x02, 0xFF} // opaque (could be plaintext or sealed)
	if err := local.Save(ctx, store.LocalDevice{DeviceID: "dev-1", PrivateKeyAtRest: blob}); err != nil {
		t.Fatalf("save local: %v", err)
	}
	got, err := local.Get(ctx)
	if err != nil {
		t.Fatalf("get local: %v", err)
	}
	if got.DeviceID != "dev-1" || !bytes.Equal(got.PrivateKeyAtRest, blob) {
		t.Fatalf("blob round-trip failed: %+v", got)
	}

	// ON DELETE CASCADE: removing the device removes the local row.
	if err := devices.Delete(ctx, "dev-1"); err != nil {
		t.Fatal(err)
	}
	if _, err := local.Get(ctx); !errors.Is(err, store.ErrNotFound) {
		t.Fatalf("expected cascade delete, got %v", err)
	}
}

func TestLocalDevice_EmptyDBIsNotFound(t *testing.T) {
	if _, err := openTemp(t).LocalDevice().Get(context.Background()); !errors.Is(err, store.ErrNotFound) {
		t.Fatalf("want ErrNotFound, got %v", err)
	}
}

func TestSecrets_Lifecycle(t *testing.T) {
	ctx := context.Background()
	repo := openTemp(t).Secrets()

	if err := repo.Create(ctx, store.Secret{
		ID: "sec-1", FolderID: "folder-A",
		EncryptedPayload: []byte("cipher"), Nonce: []byte("nonce"),
	}); err != nil {
		t.Fatalf("create: %v", err)
	}

	// Duplicate id -> ErrConflict.
	if err := repo.Create(ctx, store.Secret{
		ID: "sec-1", EncryptedPayload: []byte("x"), Nonce: []byte("y"),
	}); !errors.Is(err, store.ErrConflict) {
		t.Fatalf("want ErrConflict, got %v", err)
	}

	got, err := repo.Get(ctx, "sec-1")
	if err != nil {
		t.Fatalf("get: %v", err)
	}
	if got.Version != 1 || got.FolderID != "folder-A" || !bytes.Equal(got.EncryptedPayload, []byte("cipher")) {
		t.Fatalf("unexpected: %+v", got)
	}

	// Update (caller bumps version).
	got.EncryptedPayload = []byte("cipher2")
	got.Nonce = []byte("nonce2")
	got.Version = 2
	if err := repo.Update(ctx, &got); err != nil {
		t.Fatalf("update: %v", err)
	}
	if got, _ = repo.Get(ctx, "sec-1"); got.Version != 2 || !bytes.Equal(got.Nonce, []byte("nonce2")) {
		t.Fatalf("update not persisted: %+v", got)
	}

	// Soft delete: still gettable, excluded from List.
	if err := repo.SoftDelete(ctx, "sec-1"); err != nil {
		t.Fatalf("soft delete: %v", err)
	}

	got, err = repo.Get(ctx, "sec-1")
	if err != nil {
		t.Fatalf("get after soft delete: %v", err)
	}
	if !got.IsDeleted {
		t.Fatal("expected tombstone")
	}
	if list, _ := repo.List(ctx); len(list) != 0 {
		t.Fatalf("expected empty active list, got %d", len(list))
	}

	if err := repo.Update(ctx, &store.Secret{
		ID: "ghost", EncryptedPayload: []byte("a"), Nonce: []byte("b"),
	}); !errors.Is(err, store.ErrNotFound) {
		t.Fatalf("want ErrNotFound, got %v", err)
	}
}

func TestSecrets_EmptyFolderIsNull(t *testing.T) {
	ctx := context.Background()
	repo := openTemp(t).Secrets()
	if err := repo.Create(ctx, store.Secret{
		ID: "sec-2", EncryptedPayload: []byte("c"), Nonce: []byte("n"),
	}); err != nil {
		t.Fatal(err)
	}
	got, err := repo.Get(ctx, "sec-2")
	if err != nil {
		t.Fatal(err)
	}
	if got.FolderID != "" {
		t.Fatalf("want empty folder, got %q", got.FolderID)
	}
}

func TestRecipients_AddListRemove_InMemory(t *testing.T) {
	ctx := context.Background()
	a, err := store.Open(ctx, ":memory:")
	if err != nil {
		t.Fatalf("open memory: %v", err)
	}
	defer a.Close()

	secrets := a.Secrets()
	recs := a.Recipients()

	if err := secrets.Create(ctx, store.Secret{
		ID: "sec-9", EncryptedPayload: []byte("c"), Nonce: []byte("n"),
	}); err != nil {
		t.Fatal(err)
	}

	if err := recs.Add(ctx, store.Recipient{
		SecretID: "sec-9", DeviceID: "dev-A", EncryptedDEK: []byte("dek1"),
	}); err != nil {
		t.Fatalf("add: %v", err)
	}
	// Upsert wrapped DEK.
	if err := recs.Add(ctx, store.Recipient{
		SecretID: "sec-9", DeviceID: "dev-A", EncryptedDEK: []byte("dek2"),
	}); err != nil {
		t.Fatalf("re-add: %v", err)
	}

	list, err := recs.ListBySecret(ctx, "sec-9")
	if err != nil || len(list) != 1 {
		t.Fatalf("list: %v len=%d", err, len(list))
	}
	if !bytes.Equal(list[0].EncryptedDEK, []byte("dek2")) {
		t.Fatalf("upsert failed: %q", list[0].EncryptedDEK)
	}

	if err := recs.Remove(ctx, "sec-9", "dev-A"); err != nil {
		t.Fatalf("remove: %v", err)
	}
	if err := recs.Remove(ctx, "sec-9", "dev-A"); !errors.Is(err, store.ErrNotFound) {
		t.Fatalf("want ErrNotFound, got %v", err)
	}

	// Cascade: deleting the secret removes its recipients.
	if err := recs.Add(ctx, store.Recipient{
		SecretID: "sec-9", DeviceID: "dev-B", EncryptedDEK: []byte("dek"),
	}); err != nil {
		t.Fatal(err)
	}
	if err := secrets.SoftDelete(ctx, "sec-9"); err != nil {
		t.Fatal(err)
	}
	// Soft delete keeps recipients (tombstone, not a row delete) — verify they remain.
	if list, _ := recs.ListBySecret(ctx, "sec-9"); len(list) != 1 {
		t.Fatalf("expected recipient to survive soft delete, got %d", len(list))
	}
}
