package crypto

import (
	"bytes"
	"crypto/rand"
	"crypto/subtle"
	"encoding/base64"
	"errors"
	"fmt"
	"io"

	"filippo.io/age"
	"filippo.io/age/agessh"
	"golang.org/x/crypto/chacha20poly1305"
)

// Common errors - using sentinel errors for better error handling
var (
	ErrDecryptionFailed     = errors.New("crypto: decryption failed - authentication failed or wrong key")
	ErrInvalidKeyFormat     = errors.New("crypto: invalid key format")
	ErrKeyNotFound          = errors.New("crypto: recipient key not found")
	ErrInvalidNonceSize     = errors.New("crypto: invalid nonce size")
	ErrDecryptionAuthFailed = errors.New("crypto: decryption authentication failed")
	ErrEmptyRecipients      = errors.New("crypto: at least one recipient required")
	ErrNilEnvelope          = errors.New("crypto: envelope is nil")
	ErrEmptyCiphertext      = errors.New("crypto: ciphertext is empty")
	ErrNoWrappedDEKs        = errors.New("crypto: no wrapped DEKs")
)

const (
	// NonceSize is the size of the nonce used for ChaCha20-Poly1305
	NonceSize = chacha20poly1305.NonceSize // 12 bytes
	// KeySize is the size of the DEK (Data Encryption Key)
	KeySize = chacha20poly1305.KeySize // 32 bytes
)

// KeyPair represents an age X25519 keypair
type KeyPair struct {
	PrivateKey string // age secret key in AGE-SECRET-KEY-1... format
	PublicKey  string // age public key in age1... format
}

// Envelope represents an encrypted secret with its wrapped DEKs
type Envelope struct {
	// Ciphertext is the encrypted payload (ChaCha20-Poly1305 encrypted)
	Ciphertext []byte `json:"ciphertext"`
	// Nonce is the nonce used for symmetric encryption
	Nonce []byte `json:"nonce"`
	// WrappedDEKs maps recipient public keys to wrapped DEKs (base64 encoded age encrypted)
	WrappedDEKs map[string]string `json:"wrapped_deks"`
}

// GenerateKeyPair generates a new age X25519 keypair
func GenerateKeyPair() (*KeyPair, error) {
	identity, err := age.GenerateX25519Identity()
	if err != nil {
		return nil, fmt.Errorf("crypto: failed to generate keypair: %w", err)
	}

	return &KeyPair{
		PrivateKey: identity.String(),
		PublicKey:  identity.Recipient().String(),
	}, nil
}

// GenerateDEK generates a random Data Encryption Key (32 bytes for ChaCha20-Poly1305)
func GenerateDEK() ([]byte, error) {
	key := make([]byte, KeySize)
	if _, err := io.ReadFull(rand.Reader, key); err != nil {
		return nil, fmt.Errorf("crypto: failed to generate DEK: %w", err)
	}
	return key, nil
}

// SymmetricEncrypt encrypts plaintext using ChaCha20-Poly1305 with the given DEK
// Returns ciphertext (with auth tag appended) and nonce
func SymmetricEncrypt(plaintext []byte, dek []byte) (ciphertext []byte, nonce []byte, err error) {
	if len(dek) != KeySize {
		return nil, nil, fmt.Errorf("%w: expected %d bytes, got %d", ErrInvalidKeyFormat, KeySize, len(dek))
	}

	aead, err := chacha20poly1305.New(dek)
	if err != nil {
		return nil, nil, fmt.Errorf("crypto: failed to create AEAD: %w", err)
	}

	// Generate random nonce
	nonce = make([]byte, NonceSize)
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return nil, nil, fmt.Errorf("crypto: failed to generate nonce: %w", err)
	}

	// Seal appends the encrypted data to the dst slice (nil in this case)
	// The output is: ciphertext || auth_tag
	ciphertext = aead.Seal(nil, nonce, plaintext, nil)
	return ciphertext, nonce, nil
}

// SymmetricDecrypt decrypts ciphertext using ChaCha20-Poly1305 with the given DEK
// The ciphertext should include the authentication tag
func SymmetricDecrypt(ciphertext []byte, nonce []byte, dek []byte) ([]byte, error) {
	if len(dek) != KeySize {
		return nil, fmt.Errorf("%w: expected %d bytes, got %d", ErrInvalidKeyFormat, KeySize, len(dek))
	}

	if len(nonce) != NonceSize {
		return nil, fmt.Errorf("%w: expected %d bytes, got %d", ErrInvalidNonceSize, NonceSize, len(nonce))
	}

	aead, err := chacha20poly1305.New(dek)
	if err != nil {
		return nil, fmt.Errorf("crypto: failed to create AEAD: %w", err)
	}

	// Open decrypts and verifies the authentication tag
	plaintext, err := aead.Open(nil, nonce, ciphertext, nil)
	if err != nil {
		return nil, ErrDecryptionAuthFailed
	}

	return plaintext, nil
}

// WrapDEK wraps a DEK for a specific recipient's public key
// Returns base64-encoded age-encrypted DEK
func WrapDEK(dek []byte, recipientPubKey string) (string, error) {
	if len(dek) != KeySize {
		return "", fmt.Errorf("%w: expected %d bytes, got %d", ErrInvalidKeyFormat, KeySize, len(dek))
	}

	// Parse the recipient - try X25519 first, then SSH
	recipients := make([]age.Recipient, 0, 1)

	// Try parsing as X25519 recipient
	if x25519Recipient, err := age.ParseX25519Recipient(recipientPubKey); err == nil {
		recipients = append(recipients, x25519Recipient)
	} else if sshRecipient, err := agessh.ParseRecipient(recipientPubKey); err == nil {
		// SSH recipients implement age.Recipient interface
		recipients = append(recipients, sshRecipient)
	} else {
		return "", fmt.Errorf("crypto: failed to parse recipient key %q: unsupported format", recipientPubKey)
	}

	var buf bytes.Buffer

	// Create an age writer that encrypts to the recipient
	w, err := age.Encrypt(&buf, recipients...)
	if err != nil {
		return "", fmt.Errorf("crypto: failed to create age encryptor: %w", err)
	}

	// Write the DEK to be encrypted
	if _, err := w.Write(dek); err != nil {
		return "", fmt.Errorf("crypto: failed to write DEK: %w", err)
	}

	// Close to finalize the encryption (flushes and writes auth data)
	if err := w.Close(); err != nil {
		return "", fmt.Errorf("crypto: failed to finalize age encryption: %w", err)
	}

	// Return base64-encoded wrapped key
	return base64.StdEncoding.EncodeToString(buf.Bytes()), nil
}

// UnwrapDEK unwraps a DEK using the local private key
// The wrappedDEK should be base64-encoded age-encrypted data
func UnwrapDEK(wrappedDEK string, privateKey string) ([]byte, error) {
	// Parse the identity - try multiple formats
	identities := make([]age.Identity, 0, 1)

	// Try parsing as X25519 identity
	if x25519Identity, err := age.ParseX25519Identity(privateKey); err == nil {
		identities = append(identities, x25519Identity)
	} else if sshIdentity, err := agessh.ParseIdentity([]byte(privateKey)); err == nil {
		// SSH identities implement age.Identity interface
		identities = append(identities, sshIdentity)
	} else {
		return nil, fmt.Errorf("%w: unsupported identity format", ErrInvalidKeyFormat)
	}

	// Decode the wrapped key from base64
	wrappedBytes, err := base64.StdEncoding.DecodeString(wrappedDEK)
	if err != nil {
		return nil, fmt.Errorf("crypto: failed to decode wrapped DEK: %w", err)
	}

	// Create a reader from the wrapped key
	reader := bytes.NewReader(wrappedBytes)

	// Create an age decryptor that tries all provided identities
	r, err := age.Decrypt(reader, identities...)
	if err != nil {
		return nil, fmt.Errorf("%w: %v", ErrDecryptionFailed, err)
	}

	// Read the DEK
	dek := make([]byte, KeySize)
	n, err := io.ReadFull(r, dek)
	if err != nil {
		return nil, fmt.Errorf("%w: failed to read DEK: %v", ErrDecryptionFailed, err)
	}

	if n != KeySize {
		return nil, fmt.Errorf("%w: read %d bytes, expected %d", ErrDecryptionFailed, n, KeySize)
	}

	return dek, nil
}

// EncryptPayload encrypts a payload and wraps the DEK for multiple recipients
// This is the main entry point for encrypting secrets
func EncryptPayload(plaintext []byte, recipientPubKeys []string) (*Envelope, error) {
	if len(recipientPubKeys) == 0 {
		return nil, ErrEmptyRecipients
	}

	// Deduplicate recipients
	uniqueRecipients := make(map[string]bool)
	for _, key := range recipientPubKeys {
		uniqueRecipients[key] = true
	}

	// Generate a random DEK
	dek, err := GenerateDEK()
	if err != nil {
		return nil, err
	}
	defer secureZeroMemory(dek)

	// Symmetric encrypt the payload
	ciphertext, nonce, err := SymmetricEncrypt(plaintext, dek)
	if err != nil {
		return nil, err
	}

	// Initialize envelope
	envelope := &Envelope{
		Ciphertext:  ciphertext,
		Nonce:       nonce,
		WrappedDEKs: make(map[string]string, len(uniqueRecipients)),
	}

	// Wrap the DEK for each unique recipient
	for pubKey := range uniqueRecipients {
		wrapped, err := WrapDEK(dek, pubKey)
		if err != nil {
			return nil, fmt.Errorf("crypto: failed to wrap DEK for recipient %s: %w", pubKey, err)
		}
		envelope.WrappedDEKs[pubKey] = wrapped
	}

	return envelope, nil
}

// DecryptPayload decrypts a payload using a private key
// Tries all wrapped DEKs with the provided private key
func DecryptPayload(envelope *Envelope, privateKey string) ([]byte, error) {
	if err := VerifyEnvelopeIntegrity(envelope); err != nil {
		return nil, err
	}

	// Try each wrapped DEK until one works
	for pubKey, wrappedDEK := range envelope.WrappedDEKs {
		dek, err := UnwrapDEK(wrappedDEK, privateKey)
		if err != nil {
			// This key didn't work, try the next one
			continue
		}
		defer secureZeroMemory(dek)

		// Attempt to decrypt the payload
		plaintext, err := SymmetricDecrypt(envelope.Ciphertext, envelope.Nonce, dek)
		if err != nil {
			// DEK was unwrapped but decryption failed - corrupted data
			return nil, fmt.Errorf("crypto: payload decryption failed for recipient %s: %w", pubKey, err)
		}

		return plaintext, nil
	}

	return nil, fmt.Errorf("%w: no wrapped DEK could be decrypted with the provided key", ErrKeyNotFound)
}

// AddRecipient adds a new recipient to an existing envelope without re-encrypting the payload
// Requires an existing private key to unwrap the DEK
func AddRecipient(envelope *Envelope, existingPrivateKey string, newRecipientPubKey string) error {
	if err := VerifyEnvelopeIntegrity(envelope); err != nil {
		return err
	}

	// Check if recipient already exists
	if _, exists := envelope.WrappedDEKs[newRecipientPubKey]; exists {
		return fmt.Errorf("crypto: recipient already exists")
	}

	// Find and unwrap the DEK using our existing private key
	var dek []byte
	var err error
	unwrapped := false

	for pubKey, wrappedDEK := range envelope.WrappedDEKs {
		dek, err = UnwrapDEK(wrappedDEK, existingPrivateKey)
		if err == nil {
			unwrapped = true
			break
		}
		// Try next wrapped DEK
		_ = pubKey
	}

	if !unwrapped {
		return fmt.Errorf("%w: could not unwrap any DEK with provided key", ErrDecryptionFailed)
	}
	defer secureZeroMemory(dek)

	// Wrap the DEK for the new recipient
	newWrappedDEK, err := WrapDEK(dek, newRecipientPubKey)
	if err != nil {
		return fmt.Errorf("crypto: failed to wrap DEK for new recipient: %w", err)
	}

	// Add the new wrapped DEK
	envelope.WrappedDEKs[newRecipientPubKey] = newWrappedDEK

	return nil
}

// RemoveRecipient removes a recipient from an envelope
// Returns error if trying to remove the last recipient
func RemoveRecipient(envelope *Envelope, recipientPubKey string) error {
	if len(envelope.WrappedDEKs) <= 1 {
		return fmt.Errorf("crypto: cannot remove last recipient")
	}

	delete(envelope.WrappedDEKs, recipientPubKey)
	return nil
}

// GetRecipients returns all recipient public keys in the envelope
func GetRecipients(envelope *Envelope) []string {
	if envelope == nil || envelope.WrappedDEKs == nil {
		return nil
	}

	recipients := make([]string, 0, len(envelope.WrappedDEKs))
	for pubKey := range envelope.WrappedDEKs {
		recipients = append(recipients, pubKey)
	}
	return recipients
}

// VerifyEnvelopeIntegrity checks if the envelope structure is valid
func VerifyEnvelopeIntegrity(envelope *Envelope) error {
	if envelope == nil {
		return ErrNilEnvelope
	}

	if len(envelope.Ciphertext) == 0 {
		return ErrEmptyCiphertext
	}

	if len(envelope.Nonce) != NonceSize {
		return fmt.Errorf("%w: expected %d bytes, got %d", ErrInvalidNonceSize, NonceSize, len(envelope.Nonce))
	}

	if envelope.WrappedDEKs == nil || len(envelope.WrappedDEKs) == 0 {
		return ErrNoWrappedDEKs
	}

	return nil
}

func getPublicKeyFromPrivate(privateKey string) (string, error) {
	// Only parse as X25519 identity
	identity, err := age.ParseX25519Identity(privateKey)
	if err != nil {
		return "", fmt.Errorf("crypto: unsupported identity format, only X25519 keys supported: %w", err)
	}
	return identity.Recipient().String(), nil
}

// ValidateKeyPair checks if a public and private key form a valid pair
func ValidateKeyPair(privateKey, publicKey string) (bool, error) {
	derivedPubKey, err := getPublicKeyFromPrivate(privateKey)
	if err != nil {
		return false, err
	}

	// Constant time comparison to prevent timing attacks
	return subtle.ConstantTimeCompare([]byte(derivedPubKey), []byte(publicKey)) == 1, nil
}

// secureZeroMemory securely zeros a byte slice
// Uses constant time operation to prevent compiler optimization
func secureZeroMemory(buf []byte) {
	if len(buf) == 0 {
		return
	}
	// ConstantTimeCopy with zeros securely wipes the buffer
	subtle.ConstantTimeCopy(1, buf, make([]byte, len(buf)))
}

// EnvelopeToBytes serializes an envelope to bytes (for storage)
func EnvelopeToBytes(envelope *Envelope) ([]byte, error) {
	if err := VerifyEnvelopeIntegrity(envelope); err != nil {
		return nil, err
	}

	// Simple JSON-like serialization (use proper encoding in production)
	var buf bytes.Buffer

	// Write nonce
	buf.Write(envelope.Nonce)

	// Write number of recipients
	numRecipients := len(envelope.WrappedDEKs)
	buf.Write([]byte{byte(numRecipients)})

	// Write each recipient and wrapped DEK
	for pubKey, wrappedDEK := range envelope.WrappedDEKs {
		pubKeyBytes := []byte(pubKey)
		wrappedBytes, err := base64.StdEncoding.DecodeString(wrappedDEK)
		if err != nil {
			return nil, fmt.Errorf("crypto: invalid wrapped DEK for %s: %w", pubKey, err)
		}

		// Write lengths and data
		buf.Write([]byte{byte(len(pubKeyBytes))})
		buf.Write(pubKeyBytes)
		buf.Write([]byte{byte(len(wrappedBytes) >> 8), byte(len(wrappedBytes))})
		buf.Write(wrappedBytes)
	}

	// Write ciphertext
	buf.Write(envelope.Ciphertext)

	return buf.Bytes(), nil
}
