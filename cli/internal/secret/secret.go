// Package secret holds the client-side Secret aggregate and its ports. It
// depends only on the standard library — never on age, SQLite, or HTTP — so the
// rules stay testable in isolation and infrastructure depends on it, not the
// reverse. The crypto and vault packages are the adapters behind its ports.
package secret

import (
	"errors"
	"time"
)

// Secret is a single encrypted secret stored on a device. It holds only
// ciphertext plus metadata and owns its versioning and tombstone rules.
type Secret struct {
	ID         string
	Name       string   // local-only lookup key; never sent to the server
	FolderID   string   // optional folder/group for categorization; "" if none
	Payload    []byte   // self-contained age ciphertext (nonce + recipient stanzas embedded)
	Recipients []string // age public keys this secret is sealed to; age cannot derive them from Payload
	Version    int
	Deleted    bool
	UpdatedAt  time.Time
}

// Reseal replaces the ciphertext with a freshly sealed one and bumps the
// version. The age envelope embeds its own nonce, so none is passed here.
func (s *Secret) Reseal(payload []byte, at time.Time) {
	s.Payload = payload
	s.Version++
	s.UpdatedAt = at
}

// Delete tombstones the secret (idempotent) so the deletion can sync later.
func (s *Secret) Delete(at time.Time) {
	if s.Deleted {
		return
	}
	s.Deleted = true
	s.Version++
	s.UpdatedAt = at
}

// IsActive reports whether the secret is live (not tombstoned).
func (s *Secret) IsActive() bool { return !s.Deleted }

// Repository persists Secret aggregates. It is the port; the SQLite
// implementation is the adapter in internal/vault.
type Repository interface {
	Get(id string) (*Secret, error)
	FindByName(name string) (*Secret, error)
	List(includeDeleted bool) ([]*Secret, error)
	Save(s *Secret) error  // upsert
	Purge(id string) error // hard delete; a soft delete is Secret.Delete + Save e.g.
}

// ErrNotFound is returned by a Repository when no secret matches.
var ErrNotFound = errors.New("secret not found")
