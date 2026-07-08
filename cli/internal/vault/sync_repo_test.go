package vault_test

import (
	"errors"
	"testing"
	"time"

	"github.com/svetlana1959/GophKeeper/cli/internal/secret"
	"github.com/svetlana1959/GophKeeper/cli/internal/syncstate"
)

func TestSyncRepo_StateRoundTrip(t *testing.T) {
	db, _ := openTestDB(t)
	sr := db.Sync()

	if _, err := sr.GetState(); !errors.Is(err, syncstate.ErrNoState) {
		t.Fatalf("GetState before save err = %v, want ErrNoState", err)
	}

	st := &syncstate.State{AccountID: "acc", DeviceID: "dev", Cursor: 5}
	if err := sr.SaveState(st); err != nil {
		t.Fatalf("SaveState: %v", err)
	}
	got, err := sr.GetState()
	if err != nil {
		t.Fatalf("GetState: %v", err)
	}
	if got.AccountID != "acc" || got.DeviceID != "dev" || got.Cursor != 5 {
		t.Errorf("GetState = %+v", got)
	}

	st.Cursor = 9
	if err := sr.SaveState(st); err != nil {
		t.Fatalf("re-SaveState: %v", err)
	}
	if got, _ := sr.GetState(); got.Cursor != 9 {
		t.Errorf("cursor after update = %d, want 9", got.Cursor)
	}
}

func TestSyncRepo_DirtyTracking(t *testing.T) {
	db, _ := openTestDB(t)
	d := newDevice("d")
	mustSave(t, db.Devices().Save(d))

	s := &secret.Secret{
		ID: "s1", Name: "s1", Payload: []byte("c"),
		Recipients: []string{d.PublicKey}, Version: 1, UpdatedAt: time.Now().UTC(),
	}
	mustSave(t, db.Secrets().Save(s))

	sr := db.Sync()

	// A secret with no sync row counts as dirty (never synced), server_version 0.
	dirty, err := sr.ListDirty()
	if err != nil {
		t.Fatalf("ListDirty: %v", err)
	}
	if len(dirty) != 1 || dirty[0].SecretID != "s1" || dirty[0].ServerVersion != 0 {
		t.Fatalf("ListDirty = %+v, want s1 @0", dirty)
	}

	// After syncing it is clean.
	if err := sr.MarkSynced("s1", 3); err != nil {
		t.Fatalf("MarkSynced: %v", err)
	}
	if dirty, _ := sr.ListDirty(); len(dirty) != 0 {
		t.Fatalf("ListDirty after sync = %+v, want empty", dirty)
	}

	// A local edit re-dirties it, preserving the reconciled server_version.
	if err := sr.MarkDirty("s1"); err != nil {
		t.Fatalf("MarkDirty: %v", err)
	}
	dirty, _ = sr.ListDirty()
	if len(dirty) != 1 || dirty[0].ServerVersion != 3 {
		t.Fatalf("ListDirty after edit = %+v, want s1 @3", dirty)
	}
}
