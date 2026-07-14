// Package device holds the trusted-device model and this machine's local
// identity, plus their persistence ports. It depends only on the standard
// library — never on SQLite or HTTP — and internal/vault is the adapter behind
// its ports.
package device

import (
	"errors"
	"time"
)

// Device is a device that secrets can be shared with, identified by its age
// public key. Both the local machine and remote devices are represented here.
type Device struct {
	ID            string
	Name          string // human-readable, e.g. "laptop"
	PublicKey     string // age public key ("age1…"), the encryption recipient
	SignPublicKey string // Ed25519 signing public key (base64), verifies trust certs
	Active        bool   // false once the device is revoked
	UpdatedAt     time.Time
}

// Repository persists trusted devices. It is the port; the SQLite
// implementation is the adapter in internal/vault
type Repository interface {
	Get(id string) (*Device, error)
	FindByPublicKey(publicKey string) (*Device, error)
	List(includeInactive bool) ([]*Device, error)
	Save(d *Device) error                   // upsert
	SetActive(id string, active bool) error // activate / deactivate
}

// ErrNotFound is returned by a Repository when no device matches.
var ErrNotFound = errors.New("device not found")
