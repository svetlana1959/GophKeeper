// Package domain holds GophKeeper's client-side model and its ubiquitous
// language (Secret, Device, Recipient, ...). It depends only on the standard
// library — never on age, SQLite, or HTTP — so the rules stay testable in
// isolation and infrastructure depends on it, not the reverse.
//
// secret.go is an EXAMPLE of the intended style: a model that carries its own
// behavior (versioning, tombstone rules) rather than an anemic struct. The
// real models are implemented under their own issues.
package domain

import (
	"errors"
	"time"
)

// Secret is a single encrypted secret stored on a device. It holds only
// ciphertext plus metadata and owns its versioning and tombstone rules.
type Secret struct {
	ID        string
	Name      string // local-only lookup key; never sent to the server
	Payload   []byte // ciphertext
	Nonce     []byte
	Version   int
	Deleted   bool
	UpdatedAt time.Time
}

// Reseal replaces the ciphertext with a new envelope and bumps the version.
func (s *Secret) Reseal(payload, nonce []byte, at time.Time) {
	s.Payload, s.Nonce = payload, nonce
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

// SecretRepository persists Secret aggregates. It lives here next to the type
// it serves (the "port", in business terms, no infrastructure imports); the
// SQLite implementation is the adapter in internal/vault (#33). Each aggregate
// keeps its own repository interface in its own file — never a shared
// repository.go grab-bag.
//
// Not sure though if it has to be here, not in a separate file. Can work both ways tbh
type SecretRepository interface {
	Get(id string) (*Secret, error)
	FindByName(name string) (*Secret, error)
	List(includeDeleted bool) ([]*Secret, error)
	Save(s *Secret) error  // upsert
	Purge(id string) error // hard delete; a soft delete is Secret.Delete + Save e.g.
}

// ErrSecretNotFound is returned by a SecretRepository when no secret matches.
var ErrSecretNotFound = errors.New("secret not found")
