// Package app is the application layer: it wires the config, vault, and crypto
// adapters into the use cases the CLI commands invoke (init, set, get, delete,
// list). Commands gather input and format output; the orchestration lives here.
package app

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"time"

	"github.com/google/uuid"

	"github.com/svetlana1959/GophKeeper/cli/internal/config"
	"github.com/svetlana1959/GophKeeper/cli/internal/crypto"
	"github.com/svetlana1959/GophKeeper/cli/internal/device"
	"github.com/svetlana1959/GophKeeper/cli/internal/secret"
	"github.com/svetlana1959/GophKeeper/cli/internal/vault"
)

var (
	ErrAlreadyInitialized = errors.New("already initialized; use --force to overwrite")
	ErrNotInitialized     = errors.New("not initialized; run 'goph init' first")
	ErrSecretNotFound     = errors.New("secret not found")
	ErrNotRecipient       = errors.New("this device cannot decrypt the secret")
	ErrPINRequired        = errors.New("a PIN is required to unlock the key")
	ErrWrongPIN           = errors.New("wrong PIN")
	ErrFieldNotFound      = errors.New("field not found in secret")
)

// content is the JSON shape encrypted into a secret's payload. Name and folder
// live here (not just in local columns) so another device can fully reconstruct
// a pulled secret by decrypting it. Value is a []byte so encoding/json
// base64-encodes it, preserving binary secrets exactly.
type content struct {
	Name        string `json:"name"`
	Folder      string `json:"folder,omitempty"`
	Value       []byte `json:"value"`
	Description string `json:"description,omitempty"`
}

// InitParams are the inputs the init command gathers.
type InitParams struct {
	DeviceName string
	Remote     string // optional
	PIN        string // empty = store the private key as plaintext (0600)
	PrivateKey string // empty = generate; otherwise import this age secret key
	Force      bool
}

// InitResult is the device identity to share for enrollment.
type InitResult struct {
	DeviceID  string
	PublicKey string
}

// Init bootstraps this device: it generates or imports an age identity, writes
// config.yaml, creates the local vault, and registers the device. It refuses to
// overwrite an existing setup unless Force is set.
func Init(p InitParams) (InitResult, error) {
	store, err := config.DefaultStore()
	if err != nil {
		return InitResult{}, err
	}

	cfg := config.Default()
	cfg.Remote = p.Remote
	cfg.DeviceName = p.DeviceName

	dbPath, err := cfg.ResolveSecretDB()
	if err != nil {
		return InitResult{}, err
	}

	_, cfgErr := store.Load()
	cfgExists := cfgErr == nil
	_, dbErr := os.Stat(dbPath)
	dbExists := dbErr == nil
	if (cfgExists || dbExists) && !p.Force {
		return InitResult{}, ErrAlreadyInitialized
	}
	if p.Force && dbExists {
		if err := os.Remove(dbPath); err != nil {
			return InitResult{}, fmt.Errorf("app: reset vault: %w", err)
		}
	}

	kp, err := newOrImportedKey(p.PrivateKey)
	if err != nil {
		return InitResult{}, err
	}
	// The Ed25519 signing key is this device's trust identity (issues vouch/revoke
	// certs); always fresh, never imported alongside an age key.
	skp, err := crypto.GenerateSigningKey()
	if err != nil {
		return InitResult{}, err
	}

	// Private keys at rest: PIN-encrypted, or plaintext guarded by 0600.
	storedKey := []byte(kp.Private)
	signStoredKey := []byte(skp.Private)
	pinProtected := false
	if p.PIN != "" {
		storedKey, err = crypto.SealWithPassword([]byte(kp.Private), p.PIN)
		if err != nil {
			return InitResult{}, err
		}
		signStoredKey, err = crypto.SealWithPassword([]byte(skp.Private), p.PIN)
		if err != nil {
			return InitResult{}, err
		}
		pinProtected = true
	}

	if err := store.Save(cfg); err != nil {
		return InitResult{}, err
	}

	db, err := vault.Open(dbPath)
	if err != nil {
		return InitResult{}, err
	}
	defer db.Close()

	deviceID := uuid.NewString()
	now := time.Now().UTC()
	if err := db.Devices().Save(&device.Device{
		ID: deviceID, Name: p.DeviceName, PublicKey: kp.Public, SignPublicKey: skp.Public,
		Active: true, UpdatedAt: now,
	}); err != nil {
		return InitResult{}, err
	}
	if err := db.Local().Save(&device.LocalDevice{
		DeviceID: deviceID, StoredKey: storedKey, SignStoredKey: signStoredKey,
		PINProtected: pinProtected,
	}); err != nil {
		return InitResult{}, err
	}

	return InitResult{DeviceID: deviceID, PublicKey: kp.Public}, nil
}

func newOrImportedKey(privateKey string) (crypto.KeyPair, error) {
	if privateKey != "" {
		return crypto.ImportKeyPair(privateKey)
	}
	return crypto.GenerateKeyPair()
}

// Session is an opened GophKeeper environment: config + vault + local identity.
type Session struct {
	cfg          *config.Config
	db           *vault.DB
	secrets      secret.Repository
	local        *device.LocalDevice
	localPub     string
	localSignPub string
	cipher       secret.Cipher
}

// Open loads the config, opens the vault, and resolves the local identity. It
// returns ErrNotInitialized if the device has not been set up.
func Open() (*Session, error) {
	store, err := config.DefaultStore()
	if err != nil {
		return nil, err
	}
	cfg, err := store.Load()
	if errors.Is(err, config.ErrConfigNotFound) {
		return nil, ErrNotInitialized
	}
	if err != nil {
		return nil, err
	}

	dbPath, err := cfg.ResolveSecretDB()
	if err != nil {
		return nil, err
	}
	db, err := vault.Open(dbPath)
	if err != nil {
		return nil, err
	}

	local, err := db.Local().Get()
	if errors.Is(err, device.ErrNoLocalDevice) {
		db.Close()
		return nil, ErrNotInitialized
	}
	if err != nil {
		db.Close()
		return nil, err
	}
	dev, err := db.Devices().Get(local.DeviceID)
	if err != nil {
		db.Close()
		return nil, fmt.Errorf("app: load local device: %w", err)
	}

	return &Session{
		cfg: cfg, db: db,
		secrets: db.Secrets(),
		local:   local, localPub: dev.PublicKey, localSignPub: dev.SignPublicKey,
		cipher: crypto.Engine{},
	}, nil
}

// Close releases the vault.
func (s *Session) Close() error { return s.db.Close() }

// NeedsPIN reports whether the local private key is PIN-protected, so the
// command knows to prompt before a decrypting operation.
func (s *Session) NeedsPIN() bool { return s.local.PINProtected }

// SetParams are the inputs for creating or updating a secret.
type SetParams struct {
	Name        string
	Value       []byte
	Description string
	Folder      string
}

// Set creates a new secret sealed to this device, or updates the existing one
// with that name (re-sealing to its current recipients and bumping the version).
func (s *Session) Set(p SetParams) error {
	// Start from the existing secret, or a fresh one sealed to this device.
	sec, err := s.secrets.FindByName(p.Name)
	switch {
	case errors.Is(err, secret.ErrNotFound):
		sec = &secret.Secret{
			ID: uuid.NewString(), Name: p.Name,
			Recipients: []string{s.localPub}, Version: 0, // Reseal bumps to 1
		}
	case err != nil:
		return err
	}

	if p.Folder != "" {
		sec.FolderID = p.Folder
	}
	sec.Deleted = false // writing a value resurrects a tombstoned name

	plain, err := json.Marshal(content{
		Name: p.Name, Folder: sec.FolderID, Value: p.Value, Description: p.Description,
	})
	if err != nil {
		return fmt.Errorf("app: encode secret: %w", err)
	}

	ct, err := s.cipher.Seal(plain, sec.Recipients)
	if err != nil {
		return err
	}
	sec.Reseal(ct, time.Now().UTC()) // sets payload, bumps version, refreshes updated_at
	if err := s.secrets.Save(sec); err != nil {
		return err
	}
	return s.db.Sync().MarkDirty(sec.ID) // queue for the next push
}

// Get decrypts a secret by name and returns the requested field (default
// "value"). pin is used only when the local key is PIN-protected. Tombstoned
// secrets are reported as not found.
func (s *Session) Get(name, pin, field string) ([]byte, error) {
	sec, err := s.secrets.FindByName(name)
	if errors.Is(err, secret.ErrNotFound) {
		return nil, ErrSecretNotFound
	}
	if err != nil {
		return nil, err
	}
	if sec.Deleted {
		return nil, ErrSecretNotFound
	}

	priv, err := s.unlock(pin)
	if err != nil {
		return nil, err
	}

	plain, err := s.cipher.Open(sec.Payload, priv)
	if errors.Is(err, crypto.ErrWrongIdentity) {
		return nil, ErrNotRecipient
	}
	if err != nil {
		return nil, err
	}
	return selectField(plain, field)
}

// Delete soft-deletes a secret by name (tombstone + version bump). An already
// deleted or unknown name is reported as not found.
func (s *Session) Delete(name string) error {
	sec, err := s.secrets.FindByName(name)
	if errors.Is(err, secret.ErrNotFound) {
		return ErrSecretNotFound
	}
	if err != nil {
		return err
	}
	if sec.Deleted {
		return ErrSecretNotFound
	}
	sec.Delete(time.Now().UTC())
	if err := s.secrets.Save(sec); err != nil {
		return err
	}
	return s.db.Sync().MarkDirty(sec.ID) // queue the tombstone for the next push
}

// SecretInfo is metadata about a stored secret, with no decrypted value.
type SecretInfo struct {
	Name      string    `json:"name"`
	Folder    string    `json:"folder,omitempty"`
	Version   int       `json:"version"`
	UpdatedAt time.Time `json:"updated_at"`
	Deleted   bool      `json:"deleted"`
}

// List returns secret metadata, optionally filtered by folder and including
// tombstones.
func (s *Session) List(folder string, includeDeleted bool) ([]SecretInfo, error) {
	secs, err := s.secrets.List(includeDeleted)
	if err != nil {
		return nil, err
	}
	out := make([]SecretInfo, 0, len(secs))
	for _, sec := range secs {
		if folder != "" && sec.FolderID != folder {
			continue
		}
		out = append(out, SecretInfo{
			Name: sec.Name, Folder: sec.FolderID, Version: sec.Version,
			UpdatedAt: sec.UpdatedAt, Deleted: sec.Deleted,
		})
	}
	return out, nil
}

// unlock returns the decrypted private key, decrypting with pin when protected.
func (s *Session) unlock(pin string) (string, error) {
	return s.unlockKey(s.local.StoredKey, pin)
}

// unlockSigning returns the decrypted Ed25519 signing key (empty for a device
// that predates signing keys), decrypting with pin when protected. Used to sign
// trust certs (vouch/revoke).
func (s *Session) unlockSigning(pin string) (string, error) {
	if len(s.local.SignStoredKey) == 0 {
		return "", nil
	}
	return s.unlockKey(s.local.SignStoredKey, pin)
}

func (s *Session) unlockKey(stored []byte, pin string) (string, error) {
	if !s.local.PINProtected {
		return string(stored), nil
	}
	if pin == "" {
		return "", ErrPINRequired
	}
	plain, err := crypto.OpenWithPassword(stored, pin)
	if errors.Is(err, crypto.ErrWrongPassword) {
		return "", ErrWrongPIN
	}
	if err != nil {
		return "", err
	}
	return string(plain), nil
}

// selectField returns one field of the decrypted secret; field defaults to
// "value" (the raw, possibly binary, secret).
func selectField(plain []byte, field string) ([]byte, error) {
	var c content
	if err := json.Unmarshal(plain, &c); err != nil {
		return nil, fmt.Errorf("app: decode secret: %w", err)
	}
	switch field {
	case "", "value":
		return c.Value, nil
	case "description":
		return []byte(c.Description), nil
	default:
		return nil, fmt.Errorf("%w: %q", ErrFieldNotFound, field)
	}
}
