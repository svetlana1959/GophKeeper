package crypto

import (
	"bytes"
	"errors"
	"fmt"
	"io"

	"filippo.io/age"
)

// ErrWrongPassword is returned by OpenWithPassword when the passphrase does not
// match (or the data is corrupt).
var ErrWrongPassword = errors.New("crypto: wrong password")

// SealWithPassword encrypts data with a passphrase using age's scrypt recipient.
// It protects the device private key at rest when the user sets a PIN.
func SealWithPassword(plaintext []byte, password string) ([]byte, error) {
	r, err := age.NewScryptRecipient(password)
	if err != nil {
		return nil, fmt.Errorf("crypto: scrypt recipient: %w", err)
	}

	var buf bytes.Buffer
	w, err := age.Encrypt(&buf, r)
	if err != nil {
		return nil, fmt.Errorf("crypto: start encryption: %w", err)
	}
	if _, err := w.Write(plaintext); err != nil {
		return nil, fmt.Errorf("crypto: write plaintext: %w", err)
	}
	if err := w.Close(); err != nil {
		return nil, fmt.Errorf("crypto: finalize encryption: %w", err)
	}
	return buf.Bytes(), nil
}

// OpenWithPassword decrypts data produced by SealWithPassword, returning
// ErrWrongPassword if the passphrase is incorrect.
func OpenWithPassword(ciphertext []byte, password string) ([]byte, error) {
	id, err := age.NewScryptIdentity(password)
	if err != nil {
		return nil, fmt.Errorf("crypto: scrypt identity: %w", err)
	}

	r, err := age.Decrypt(bytes.NewReader(ciphertext), id)
	if err != nil {
		return nil, ErrWrongPassword
	}
	return io.ReadAll(r)
}
