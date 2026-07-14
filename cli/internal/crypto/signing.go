package crypto

import (
	"crypto/ed25519"
	"crypto/rand"
	"encoding/base64"
	"errors"
	"fmt"
)

// ErrBadSignature is returned by Verify when a signature does not match the
// message under the given public key.
var ErrBadSignature = errors.New("crypto: signature does not verify")

// SigningKeyPair is an Ed25519 device signing identity, separate from the age
// (X25519) encryption identity. age keys can encrypt but not sign, so a device
// carries this too in order to issue verifiable trust certs (vouch/revoke).
//
// Both halves are base64 (raw std) strings: Public is the 32-byte verifying key
// (safe to publish); Private is the 64-byte signing key (kept next to the age
// key at rest).
type SigningKeyPair struct {
	Public  string
	Private string
}

// GenerateSigningKey creates a fresh Ed25519 signing identity.
func GenerateSigningKey() (SigningKeyPair, error) {
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		return SigningKeyPair{}, fmt.Errorf("crypto: generate signing key: %w", err)
	}
	return SigningKeyPair{
		Public:  base64.RawStdEncoding.EncodeToString(pub),
		Private: base64.RawStdEncoding.EncodeToString(priv),
	}, nil
}

// Sign signs message with an Ed25519 private key (as produced by
// GenerateSigningKey), returning a base64 (raw std) signature. It returns
// ErrInvalidKey if privateKey does not decode to a valid signing key.
func Sign(privateKey string, message []byte) (string, error) {
	priv, err := decodeSigningPrivate(privateKey)
	if err != nil {
		return "", err
	}
	sig := ed25519.Sign(priv, message)
	return base64.RawStdEncoding.EncodeToString(sig), nil
}

// Verify checks a base64 signature over message against an Ed25519 public key.
// It returns ErrInvalidKey if publicKey or signature do not decode, and
// ErrBadSignature if they decode but the signature does not match.
func Verify(publicKey string, message []byte, signature string) error {
	pub, err := decodeSigningPublic(publicKey)
	if err != nil {
		return err
	}
	sig, err := base64.RawStdEncoding.DecodeString(signature)
	if err != nil {
		return fmt.Errorf("%w: signature: %v", ErrInvalidKey, err)
	}
	if !ed25519.Verify(pub, message, sig) {
		return ErrBadSignature
	}
	return nil
}

func decodeSigningPrivate(s string) (ed25519.PrivateKey, error) {
	raw, err := base64.RawStdEncoding.DecodeString(s)
	if err != nil {
		return nil, fmt.Errorf("%w: signing private: %v", ErrInvalidKey, err)
	}
	if len(raw) != ed25519.PrivateKeySize {
		return nil, fmt.Errorf("%w: signing private: wrong size", ErrInvalidKey)
	}
	return ed25519.PrivateKey(raw), nil
}

func decodeSigningPublic(s string) (ed25519.PublicKey, error) {
	raw, err := base64.RawStdEncoding.DecodeString(s)
	if err != nil {
		return nil, fmt.Errorf("%w: signing public: %v", ErrInvalidKey, err)
	}
	if len(raw) != ed25519.PublicKeySize {
		return nil, fmt.Errorf("%w: signing public: wrong size", ErrInvalidKey)
	}
	return ed25519.PublicKey(raw), nil
}
