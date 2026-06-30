package crypto

import (
	"bytes"
	"errors"
	"fmt"
	"io"

	"filippo.io/age"

	"github.com/svetlana1959/GophKeeper/cli/internal/secret"
)

var (
	ErrNoRecipients  = errors.New("crypto: at least one recipient required")
	ErrInvalidKey    = errors.New("crypto: invalid age key")
	ErrWrongIdentity = errors.New("crypto: secret is not sealed to this identity")
)

// KeyPair is an age X25519 identity. Public is an "age1…" recipient (safe to
// publish); Private is an "AGE-SECRET-KEY-1…" key (store in the OS keyring).
type KeyPair struct {
	Public  string
	Private string
}

// GenerateKeyPair creates a fresh device identity.
func GenerateKeyPair() (KeyPair, error) {
	id, err := age.GenerateX25519Identity()
	if err != nil {
		return KeyPair{}, fmt.Errorf("crypto: generate identity: %w", err)
	}
	return KeyPair{Public: id.Recipient().String(), Private: id.String()}, nil
}

// ImportKeyPair derives the public key from an existing age private key, for
// adopting an identity generated elsewhere. It returns ErrInvalidKey if the key
// does not parse.
func ImportKeyPair(privateKey string) (KeyPair, error) {
	id, err := age.ParseX25519Identity(privateKey)
	if err != nil {
		return KeyPair{}, fmt.Errorf("%w: %v", ErrInvalidKey, err)
	}
	return KeyPair{Public: id.Recipient().String(), Private: id.String()}, nil
}

// Engine implements secret.Cipher over age. It is stateless; the zero value is
// ready to use.
type Engine struct{}

// Compile-time guarantee that Engine satisfies the secret port.
var _ secret.Cipher = Engine{}

// Seal encrypts plaintext to every recipient. Any one recipient's private key
// can Open the result, which is a self-contained age ciphertext — store it
// verbatim. Keeping the recipient set unique is the caller's concern.
func (Engine) Seal(plaintext []byte, recipients []string) ([]byte, error) {
	recs, err := parseRecipients(recipients)
	if err != nil {
		return nil, err
	}

	var buf bytes.Buffer
	w, err := age.Encrypt(&buf, recs...)
	if err != nil {
		return nil, fmt.Errorf("crypto: start encryption: %w", err)
	}
	if _, err := w.Write(plaintext); err != nil {
		return nil, fmt.Errorf("crypto: write plaintext: %w", err)
	}
	if err := w.Close(); err != nil { // flushes and writes the auth tag
		return nil, fmt.Errorf("crypto: finalize encryption: %w", err)
	}
	return buf.Bytes(), nil
}

// Open decrypts a sealed secret. It returns ErrWrongIdentity if privateKey is
// not one of the recipients, and a distinct error if the ciphertext is
// corrupted or tampered with.
func (Engine) Open(ciphertext []byte, privateKey string) ([]byte, error) {
	id, err := age.ParseX25519Identity(privateKey)
	if err != nil {
		return nil, fmt.Errorf("%w: %v", ErrInvalidKey, err)
	}

	r, err := age.Decrypt(bytes.NewReader(ciphertext), id)
	if err != nil {
		var noMatch *age.NoIdentityMatchError
		if errors.As(err, &noMatch) {
			return nil, ErrWrongIdentity
		}
		return nil, fmt.Errorf("crypto: decrypt: %w", err) // tampered or corrupt
	}
	plaintext, err := io.ReadAll(r)
	if err != nil {
		return nil, fmt.Errorf("crypto: read plaintext: %w", err)
	}
	return plaintext, nil
}

// Reshare re-encrypts a secret to a new recipient set, minting a fresh file key.
// privateKey must currently be a recipient. This is how recipients are added or
// removed: a removed recipient loses access to the new ciphertext (the key is
// rotated), not merely its header entry.
func (e Engine) Reshare(ciphertext []byte, privateKey string, recipients []string) ([]byte, error) {
	plaintext, err := e.Open(ciphertext, privateKey)
	if err != nil {
		return nil, err
	}
	return e.Seal(plaintext, recipients)
}

func parseRecipients(keys []string) ([]age.Recipient, error) {
	if len(keys) == 0 {
		return nil, ErrNoRecipients
	}
	recs := make([]age.Recipient, 0, len(keys))
	for _, k := range keys {
		r, err := age.ParseX25519Recipient(k)
		if err != nil {
			return nil, fmt.Errorf("%w: %q: %v", ErrInvalidKey, k, err)
		}
		recs = append(recs, r)
	}
	return recs, nil
}
