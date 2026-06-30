// Package syncstate holds this device's synchronization bookkeeping: its binding
// to the server account, the pull cursor, and which secrets still need pushing.
// It depends only on the standard library; internal/vault is the adapter behind
// its port.
package syncstate

import "errors"

// State is this device's binding to a server account plus its pull cursor.
type State struct {
	AccountID string
	DeviceID  string // server-assigned device id
	Cursor    int64  // highest server seq applied so far
}

// Dirty is a secret awaiting push, with the server version to push against
// (0 for one never synced).
type Dirty struct {
	SecretID      string
	ServerVersion int
}

// Repository persists sync state. It is the port; the SQLite implementation is
// the adapter in internal/vault.
type Repository interface {
	GetState() (*State, error) // ErrNoState before the first sync
	SaveState(s *State) error
	MarkDirty(secretID string) error                    // a local change needs push
	MarkSynced(secretID string, serverVersion int) error // reconciled with the server
	ListDirty() ([]Dirty, error)                        // secrets needing push
}

// ErrNoState is returned by GetState before this device has synced.
var ErrNoState = errors.New("sync state not initialized")
