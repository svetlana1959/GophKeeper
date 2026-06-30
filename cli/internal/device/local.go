package device

import "errors"

// LocalDevice is this machine's identity: its device id and its age private key
// as stored at rest. The key bytes are PIN-encrypted when PINProtected is true
// and plaintext (guarded by 0600 file permissions) otherwise. The vault never
// interprets StoredKey — it only persists and returns it; deriving a PIN key and
// decrypting is an application concern.
type LocalDevice struct {
	DeviceID     string
	StoredKey    []byte // age private key at rest, encrypted iff PINProtected
	PINProtected bool
}

// LocalRepository stores the single local device (1:1). It is the port; the
// SQLite implementation is the adapter in internal/vault
type LocalRepository interface {
	Get() (*LocalDevice, error)
	Save(ld *LocalDevice) error
}

// ErrNoLocalDevice is returned by LocalRepository.Get before init has run.
var ErrNoLocalDevice = errors.New("local device not initialized")
