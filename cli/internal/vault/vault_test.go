package vault_test

import (
	"database/sql"
	"errors"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/svetlana1959/GophKeeper/cli/internal/device"
	"github.com/svetlana1959/GophKeeper/cli/internal/secret"
	"github.com/svetlana1959/GophKeeper/cli/internal/vault"

	_ "modernc.org/sqlite"
)

// openTestDB opens a vault on a fresh temp file and returns it with its path.
func openTestDB(t *testing.T) (*vault.DB, string) {
	t.Helper()
	path := filepath.Join(t.TempDir(), "test.db")
	db, err := vault.Open(path)
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	t.Cleanup(func() { db.Close() })
	return db, path
}

func newDevice(name string) *device.Device {
	return &device.Device{
		ID:            name + "-id",
		Name:          name,
		PublicKey:     "age1-pub-" + name,
		SignPublicKey: "sign-pub-" + name,
		Active:        true,
		UpdatedAt:     time.Now().UTC(),
	}
}

func TestOpen_CreatesSecureFileAndIsIdempotent(t *testing.T) {
	path := filepath.Join(t.TempDir(), "sub", "test.db")

	db, err := vault.Open(path)
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	db.Close()

	if info, err := os.Stat(path); err != nil {
		t.Fatalf("stat db: %v", err)
	} else if perm := info.Mode().Perm(); perm != 0o600 {
		t.Errorf("db perm = %v, want 0600", perm)
	}
	if info, err := os.Stat(filepath.Dir(path)); err != nil {
		t.Fatalf("stat dir: %v", err)
	} else if perm := info.Mode().Perm(); perm != 0o700 {
		t.Errorf("dir perm = %v, want 0700", perm)
	}

	// Reopening an existing database must not fail (idempotent migrations).
	db2, err := vault.Open(path)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	db2.Close()
}

func TestDeviceRepo_CRUD(t *testing.T) {
	db, _ := openTestDB(t)
	repo := db.Devices()

	d := newDevice("laptop")
	if err := repo.Save(d); err != nil {
		t.Fatalf("Save: %v", err)
	}

	got, err := repo.Get(d.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got.Name != d.Name || got.PublicKey != d.PublicKey || !got.Active {
		t.Errorf("Get = %+v", got)
	}
	if got.SignPublicKey != d.SignPublicKey {
		t.Errorf("SignPublicKey = %q, want %q", got.SignPublicKey, d.SignPublicKey)
	}
	if !got.UpdatedAt.Equal(d.UpdatedAt) {
		t.Errorf("UpdatedAt = %v, want %v", got.UpdatedAt, d.UpdatedAt)
	}

	byPub, err := repo.FindByPublicKey(d.PublicKey)
	if err != nil || byPub.ID != d.ID {
		t.Errorf("FindByPublicKey = %+v, %v", byPub, err)
	}

	d.Name = "renamed"
	if err := repo.Save(d); err != nil {
		t.Fatalf("re-Save: %v", err)
	}
	if got, _ := repo.Get(d.ID); got.Name != "renamed" {
		t.Errorf("upsert name = %q, want renamed", got.Name)
	}

	if _, err := repo.Get("missing"); !errors.Is(err, device.ErrNotFound) {
		t.Errorf("Get(missing) err = %v, want ErrNotFound", err)
	}
}

func TestDeviceRepo_SetActiveAndList(t *testing.T) {
	db, _ := openTestDB(t)
	repo := db.Devices()
	a, b := newDevice("a"), newDevice("b")
	mustSave(t, repo.Save(a), repo.Save(b))

	if err := repo.SetActive(b.ID, false); err != nil {
		t.Fatalf("SetActive: %v", err)
	}

	active, err := repo.List(false)
	if err != nil {
		t.Fatalf("List active: %v", err)
	}
	if len(active) != 1 || active[0].ID != a.ID {
		t.Errorf("active = %+v", active)
	}
	if all, _ := repo.List(true); len(all) != 2 {
		t.Errorf("all len = %d, want 2", len(all))
	}

	if err := repo.SetActive("missing", true); !errors.Is(err, device.ErrNotFound) {
		t.Errorf("SetActive(missing) err = %v, want ErrNotFound", err)
	}
}

func TestLocalRepo(t *testing.T) {
	db, _ := openTestDB(t)

	if _, err := db.Local().Get(); !errors.Is(err, device.ErrNoLocalDevice) {
		t.Errorf("Get before init err = %v, want ErrNoLocalDevice", err)
	}

	d := newDevice("this")
	if err := db.Devices().Save(d); err != nil { // FK: device must exist first
		t.Fatalf("Save device: %v", err)
	}

	ld := &device.LocalDevice{
		DeviceID: d.ID, StoredKey: []byte("encrypted"),
		SignStoredKey: []byte("sign-encrypted"), PINProtected: true,
	}
	if err := db.Local().Save(ld); err != nil {
		t.Fatalf("Save local: %v", err)
	}

	got, err := db.Local().Get()
	if err != nil {
		t.Fatalf("Get local: %v", err)
	}
	if got.DeviceID != d.ID || !got.PINProtected || string(got.StoredKey) != "encrypted" {
		t.Errorf("Get local = %+v", got)
	}
	if string(got.SignStoredKey) != "sign-encrypted" {
		t.Errorf("SignStoredKey = %q, want %q", got.SignStoredKey, "sign-encrypted")
	}

	// A nil signing key (legacy/partial record) must persist as an empty blob,
	// not trip the NOT NULL constraint.
	if err := db.Local().Save(&device.LocalDevice{DeviceID: d.ID, StoredKey: []byte("k")}); err != nil {
		t.Fatalf("Save local with nil signing key: %v", err)
	}
	if got, _ := db.Local().Get(); len(got.SignStoredKey) != 0 {
		t.Errorf("nil signing key round-trip = %q, want empty", got.SignStoredKey)
	}

	// Save replaces the single row.
	ld.PINProtected = false
	ld.StoredKey = []byte("plain")
	if err := db.Local().Save(ld); err != nil {
		t.Fatalf("re-Save local: %v", err)
	}
	if got, _ := db.Local().Get(); got.PINProtected || string(got.StoredKey) != "plain" {
		t.Errorf("replace failed: %+v", got)
	}
}

func TestSecretRepo_RoundTripWithRecipients(t *testing.T) {
	db, _ := openTestDB(t)
	d1, d2 := newDevice("d1"), newDevice("d2")
	mustSave(t, db.Devices().Save(d1), db.Devices().Save(d2))

	repo := db.Secrets()
	s := &secret.Secret{
		ID:         "s1",
		Name:       "github",
		FolderID:   "work",
		Payload:    []byte("age-ciphertext"),
		Recipients: []string{d1.PublicKey, d2.PublicKey},
		Version:    1,
		UpdatedAt:  time.Now().UTC(),
	}
	if err := repo.Save(s); err != nil {
		t.Fatalf("Save: %v", err)
	}

	got, err := repo.Get("s1")
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got.Name != "github" || got.FolderID != "work" || string(got.Payload) != "age-ciphertext" || got.Version != 1 {
		t.Errorf("Get = %+v", got)
	}
	if !got.UpdatedAt.Equal(s.UpdatedAt) {
		t.Errorf("UpdatedAt = %v, want %v", got.UpdatedAt, s.UpdatedAt)
	}
	if !sameSet(got.Recipients, s.Recipients) {
		t.Errorf("Recipients = %v, want %v", got.Recipients, s.Recipients)
	}

	if byName, err := repo.FindByName("github"); err != nil || byName.ID != "s1" {
		t.Errorf("FindByName = %+v, %v", byName, err)
	}
}

// A recipient that is not a trusted device fails, and the whole Save rolls back.
func TestSecretRepo_UnknownRecipientRollsBack(t *testing.T) {
	db, _ := openTestDB(t)
	repo := db.Secrets()

	s := &secret.Secret{
		ID: "x", Name: "x", Payload: []byte("c"),
		Recipients: []string{"age1-unknown"}, Version: 1, UpdatedAt: time.Now().UTC(),
	}
	if err := repo.Save(s); !errors.Is(err, device.ErrNotFound) {
		t.Errorf("Save err = %v, want device.ErrNotFound", err)
	}
	if _, err := repo.Get("x"); !errors.Is(err, secret.ErrNotFound) {
		t.Errorf("secret must not persist on recipient failure: %v", err)
	}
}

func TestSecretRepo_SoftDeleteAndList(t *testing.T) {
	db, _ := openTestDB(t)
	d := newDevice("d")
	mustSave(t, db.Devices().Save(d))
	repo := db.Secrets()

	live := &secret.Secret{ID: "live", Name: "live", Payload: []byte("a"), Recipients: []string{d.PublicKey}, Version: 1, UpdatedAt: time.Now().UTC()}
	gone := &secret.Secret{ID: "gone", Name: "gone", Payload: []byte("b"), Recipients: []string{d.PublicKey}, Version: 1, UpdatedAt: time.Now().UTC()}
	mustSave(t, repo.Save(live), repo.Save(gone))

	gone.Delete(time.Now().UTC())
	if err := repo.Save(gone); err != nil {
		t.Fatalf("soft delete Save: %v", err)
	}

	visible, err := repo.List(false)
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(visible) != 1 || visible[0].ID != "live" {
		t.Errorf("List(false) = %+v", visible)
	}
	if all, _ := repo.List(true); len(all) != 2 {
		t.Errorf("List(true) len = %d, want 2", len(all))
	}
}

// Purge hard-deletes and cascades to secret_recipients (proves foreign_keys is
// enabled on the vault connection).
func TestSecretRepo_PurgeCascades(t *testing.T) {
	db, path := openTestDB(t)
	d := newDevice("d")
	mustSave(t, db.Devices().Save(d))
	repo := db.Secrets()

	s := &secret.Secret{ID: "s", Name: "s", Payload: []byte("c"), Recipients: []string{d.PublicKey}, Version: 1, UpdatedAt: time.Now().UTC()}
	mustSave(t, repo.Save(s))

	if err := repo.Purge("s"); err != nil {
		t.Fatalf("Purge: %v", err)
	}
	if _, err := repo.Get("s"); !errors.Is(err, secret.ErrNotFound) {
		t.Errorf("Get after purge err = %v, want ErrNotFound", err)
	}
	if n := countRecipients(t, path, "s"); n != 0 {
		t.Errorf("secret_recipients after purge = %d rows, want 0 (cascade failed)", n)
	}

	if err := repo.Purge("missing"); !errors.Is(err, secret.ErrNotFound) {
		t.Errorf("Purge(missing) err = %v, want ErrNotFound", err)
	}
}

// countRecipients reads the junction directly to verify cascade behavior.
func countRecipients(t *testing.T, path, secretID string) int {
	t.Helper()
	raw, err := sql.Open("sqlite", "file:"+path)
	if err != nil {
		t.Fatalf("raw open: %v", err)
	}
	defer raw.Close()
	var n int
	if err := raw.QueryRow(`SELECT COUNT(*) FROM secret_recipients WHERE secret_id = ?`, secretID).Scan(&n); err != nil {
		t.Fatalf("count: %v", err)
	}
	return n
}

func mustSave(t *testing.T, errs ...error) {
	t.Helper()
	for _, err := range errs {
		if err != nil {
			t.Fatalf("setup save: %v", err)
		}
	}
}

func sameSet(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	seen := make(map[string]int, len(a))
	for _, x := range a {
		seen[x]++
	}
	for _, x := range b {
		seen[x]--
	}
	for _, c := range seen {
		if c != 0 {
			return false
		}
	}
	return true
}
