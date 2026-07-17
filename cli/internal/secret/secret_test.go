package secret

import (
	"testing"
	"time"
)

func TestReseal_ReplacesPayloadAndBumpsVersion(t *testing.T) {
	s := &Secret{ID: "1", Version: 1, Payload: []byte("old")}
	at := time.Date(2026, 7, 17, 12, 0, 0, 0, time.UTC)

	s.Reseal([]byte("new"), at)

	if string(s.Payload) != "new" {
		t.Errorf("payload = %q, want new", s.Payload)
	}
	if s.Version != 2 {
		t.Errorf("version = %d, want 2", s.Version)
	}
	if !s.UpdatedAt.Equal(at) {
		t.Errorf("updated_at = %v, want %v", s.UpdatedAt, at)
	}
}

func TestDelete_TombstonesOnceAndIsIdempotent(t *testing.T) {
	s := &Secret{Version: 3}
	first := time.Date(2026, 7, 17, 12, 0, 0, 0, time.UTC)

	s.Delete(first)
	if !s.Deleted {
		t.Fatal("not tombstoned after Delete")
	}
	if s.Version != 4 {
		t.Errorf("version = %d, want 4", s.Version)
	}

	// A second delete is a no-op: no version bump, no timestamp change.
	s.Delete(first.Add(time.Hour))
	if s.Version != 4 {
		t.Errorf("second delete bumped version to %d, want 4", s.Version)
	}
	if !s.UpdatedAt.Equal(first) {
		t.Errorf("second delete moved updated_at to %v, want %v", s.UpdatedAt, first)
	}
}

func TestIsActive_TracksTombstone(t *testing.T) {
	s := &Secret{}
	if !s.IsActive() {
		t.Error("fresh secret should be active")
	}
	s.Delete(time.Now())
	if s.IsActive() {
		t.Error("tombstoned secret should not be active")
	}
}
