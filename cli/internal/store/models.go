package store

import "time"

// TrustedDevice maps to the trusted_devices table (local or remote device).
type TrustedDevice struct {
	ID        string // device UUID
	Name      string // human-readable, e.g. "laptop-asus"
	PublicKey string // AGE public key (age1...)
	IsActive  bool
	UpdatedAt time.Time
}

// LocalDevice maps to the local_device table (1:1 with this machine).
//
// PrivateKeyAtRest is whatever blob the CLI produced: PIN-encrypted, or
// plaintext when the user chose no PIN. The store treats it as opaque bytes.
type LocalDevice struct {
	DeviceID         string
	PrivateKeyAtRest []byte
	CreatedAt        time.Time
}

// Secret maps to the secrets table. Payload is always ciphertext.
type Secret struct {
	ID               string // secret UUID (matches server)
	FolderID         string // optional; empty == NULL in DB
	EncryptedPayload []byte // ChaCha20-Poly1305 / AES-GCM ciphertext
	Nonce            []byte
	Version          int
	IsDeleted        bool // tombstone
	CreatedAt        time.Time
	UpdatedAt        time.Time
}

// Recipient maps to the secret_recipients table: one wrapped DEK per device.
type Recipient struct {
	SecretID     string
	DeviceID     string
	EncryptedDEK []byte // DEK asymmetrically wrapped with the device AGE key
}
