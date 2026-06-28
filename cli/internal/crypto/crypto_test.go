package crypto

import (
	"bytes"
	"encoding/base64"
	"errors"
	"fmt"
	"strings"
	"sync"
	"testing"
)

// TestGenerateKeyPair tests key pair generation
func TestGenerateKeyPair(t *testing.T) {
	t.Run("Basic key generation", func(t *testing.T) {
		kp, err := GenerateKeyPair()
		if err != nil {
			t.Fatalf("GenerateKeyPair() unexpected error: %v", err)
		}

		if kp.PrivateKey == "" {
			t.Error("PrivateKey should not be empty")
		}
		if kp.PublicKey == "" {
			t.Error("PublicKey should not be empty")
		}
		if !strings.HasPrefix(kp.PublicKey, "age1") {
			t.Errorf("PublicKey should start with 'age1', got: %s", kp.PublicKey)
		}
		if !strings.HasPrefix(kp.PrivateKey, "AGE-SECRET-KEY-1") {
			t.Errorf("PrivateKey should start with 'AGE-SECRET-KEY-1', got: %s", kp.PrivateKey)
		}
	})

	t.Run("Multiple generations produce unique keys", func(t *testing.T) {
		kp1, err1 := GenerateKeyPair()
		kp2, err2 := GenerateKeyPair()
		if err1 != nil || err2 != nil {
			t.Fatal("GenerateKeyPair() should not error")
		}

		if kp1.PublicKey == kp2.PublicKey {
			t.Error("Generated public keys should be unique")
		}
		if kp1.PrivateKey == kp2.PrivateKey {
			t.Error("Generated private keys should be unique")
		}
	})

	t.Run("Key pair validation", func(t *testing.T) {
		kp, _ := GenerateKeyPair()

		valid, err := ValidateKeyPair(kp.PrivateKey, kp.PublicKey)
		if err != nil {
			t.Fatalf("ValidateKeyPair() unexpected error: %v", err)
		}
		if !valid {
			t.Error("Generated key pair should be valid")
		}
	})

	t.Run("Invalid key pair", func(t *testing.T) {
		kp1, _ := GenerateKeyPair()
		kp2, _ := GenerateKeyPair()

		valid, err := ValidateKeyPair(kp1.PrivateKey, kp2.PublicKey)
		if err != nil {
			t.Fatalf("ValidateKeyPair() unexpected error: %v", err)
		}
		if valid {
			t.Error("Different public/private keys should not be valid")
		}
	})
}

// TestGenerateDEK tests DEK generation
func TestGenerateDEK(t *testing.T) {
	t.Run("Basic DEK generation", func(t *testing.T) {
		dek, err := GenerateDEK()
		if err != nil {
			t.Fatalf("GenerateDEK() unexpected error: %v", err)
		}

		if len(dek) != KeySize {
			t.Errorf("DEK length = %d, want %d", len(dek), KeySize)
		}
	})

	t.Run("Multiple DEKs are unique", func(t *testing.T) {
		dek1, _ := GenerateDEK()
		dek2, _ := GenerateDEK()

		if bytes.Equal(dek1, dek2) {
			t.Error("Generated DEKs should be unique")
		}
	})

	t.Run("DEK is not all zeros", func(t *testing.T) {
		dek, _ := GenerateDEK()
		zeros := make([]byte, KeySize)

		if bytes.Equal(dek, zeros) {
			t.Error("DEK should not be all zeros")
		}
	})
}

// TestSymmetricEncryptDecrypt tests symmetric encryption/decryption
func TestSymmetricEncryptDecrypt(t *testing.T) {
	t.Run("Basic encrypt/decrypt", func(t *testing.T) {
		plaintext := []byte("Hello, World!")
		dek, _ := GenerateDEK()

		ciphertext, nonce, err := SymmetricEncrypt(plaintext, dek)
		if err != nil {
			t.Fatalf("SymmetricEncrypt() unexpected error: %v", err)
		}

		if len(ciphertext) == 0 {
			t.Error("Ciphertext should not be empty")
		}
		if len(nonce) != NonceSize {
			t.Errorf("Nonce length = %d, want %d", len(nonce), NonceSize)
		}
		// Ciphertext should be different from plaintext
		if bytes.Equal(ciphertext[:len(plaintext)], plaintext) {
			t.Error("Ciphertext should not equal plaintext")
		}

		decrypted, err := SymmetricDecrypt(ciphertext, nonce, dek)
		if err != nil {
			t.Fatalf("SymmetricDecrypt() unexpected error: %v", err)
		}

		if !bytes.Equal(plaintext, decrypted) {
			t.Errorf("Decrypted text doesn't match: got %q, want %q", decrypted, plaintext)
		}
	})

	t.Run("Empty plaintext", func(t *testing.T) {
		plaintext := []byte{}
		dek, _ := GenerateDEK()

		ciphertext, nonce, err := SymmetricEncrypt(plaintext, dek)
		if err != nil {
			t.Fatalf("SymmetricEncrypt() unexpected error: %v", err)
		}

		decrypted, err := SymmetricDecrypt(ciphertext, nonce, dek)
		if err != nil {
			t.Fatalf("SymmetricDecrypt() unexpected error: %v", err)
		}

		if !bytes.Equal(plaintext, decrypted) {
			t.Error("Should handle empty plaintext")
		}
	})

	t.Run("Large plaintext", func(t *testing.T) {
		plaintext := bytes.Repeat([]byte("A"), 1024*1024) // 1MB
		dek, _ := GenerateDEK()

		ciphertext, nonce, err := SymmetricEncrypt(plaintext, dek)
		if err != nil {
			t.Fatalf("SymmetricEncrypt() unexpected error: %v", err)
		}

		decrypted, err := SymmetricDecrypt(ciphertext, nonce, dek)
		if err != nil {
			t.Fatalf("SymmetricDecrypt() unexpected error: %v", err)
		}

		if !bytes.Equal(plaintext, decrypted) {
			t.Error("Failed to handle large plaintext")
		}
	})

	t.Run("Invalid DEK size for encrypt", func(t *testing.T) {
		plaintext := []byte("test")
		badDek := []byte("short")

		_, _, err := SymmetricEncrypt(plaintext, badDek)
		if err == nil {
			t.Error("Should fail with invalid DEK size")
		}
		if !errors.Is(err, ErrInvalidKeyFormat) {
			t.Errorf("Expected ErrInvalidKeyFormat, got %v", err)
		}
	})

	t.Run("Invalid DEK size for decrypt", func(t *testing.T) {
		dek, _ := GenerateDEK()
		plaintext := []byte("test")
		ciphertext, nonce, _ := SymmetricEncrypt(plaintext, dek)

		_, err := SymmetricDecrypt(ciphertext, nonce, []byte("short"))
		if err == nil {
			t.Error("Should fail with invalid DEK size")
		}
		if !errors.Is(err, ErrInvalidKeyFormat) {
			t.Errorf("Expected ErrInvalidKeyFormat, got %v", err)
		}
	})

	t.Run("Invalid nonce size", func(t *testing.T) {
		dek, _ := GenerateDEK()

		_, err := SymmetricDecrypt([]byte("ciphertext"), []byte("short"), dek)
		if err == nil {
			t.Error("Should fail with invalid nonce size")
		}
		if !errors.Is(err, ErrInvalidNonceSize) {
			t.Errorf("Expected ErrInvalidNonceSize, got %v", err)
		}
	})

	t.Run("Wrong DEK", func(t *testing.T) {
		plaintext := []byte("test")
		dek1, _ := GenerateDEK()
		dek2, _ := GenerateDEK()

		ciphertext, nonce, _ := SymmetricEncrypt(plaintext, dek1)
		_, err := SymmetricDecrypt(ciphertext, nonce, dek2)
		if err == nil {
			t.Error("Should fail with wrong DEK")
		}
		if !errors.Is(err, ErrDecryptionAuthFailed) {
			t.Errorf("Expected ErrDecryptionAuthFailed, got %v", err)
		}
	})

	t.Run("Wrong nonce", func(t *testing.T) {
		plaintext := []byte("test")
		dek, _ := GenerateDEK()

		ciphertext, nonce, _ := SymmetricEncrypt(plaintext, dek)
		badNonce := make([]byte, NonceSize)
		copy(badNonce, nonce)
		badNonce[0] ^= 0xFF // Flip bits

		_, err := SymmetricDecrypt(ciphertext, badNonce, dek)
		if err == nil {
			t.Error("Should fail with wrong nonce")
		}
		if !errors.Is(err, ErrDecryptionAuthFailed) {
			t.Errorf("Expected ErrDecryptionAuthFailed, got %v", err)
		}
	})

	t.Run("Tampered ciphertext", func(t *testing.T) {
		plaintext := []byte("test")
		dek, _ := GenerateDEK()

		ciphertext, nonce, _ := SymmetricEncrypt(plaintext, dek)
		tampered := make([]byte, len(ciphertext))
		copy(tampered, ciphertext)
		tampered[0] ^= 0xFF

		_, err := SymmetricDecrypt(tampered, nonce, dek)
		if err == nil {
			t.Error("Should detect tampered ciphertext")
		}
		if !errors.Is(err, ErrDecryptionAuthFailed) {
			t.Errorf("Expected ErrDecryptionAuthFailed, got %v", err)
		}
	})

	t.Run("Truncated ciphertext", func(t *testing.T) {
		plaintext := []byte("test")
		dek, _ := GenerateDEK()

		ciphertext, nonce, _ := SymmetricEncrypt(plaintext, dek)
		_, err := SymmetricDecrypt(ciphertext[:len(ciphertext)-1], nonce, dek)
		if err == nil {
			t.Error("Should fail with truncated ciphertext")
		}
	})

	t.Run("Unique nonces", func(t *testing.T) {
		plaintext := []byte("test")
		dek, _ := GenerateDEK()

		_, nonce1, _ := SymmetricEncrypt(plaintext, dek)
		_, nonce2, _ := SymmetricEncrypt(plaintext, dek)

		if bytes.Equal(nonce1, nonce2) {
			t.Error("Nonces should be unique")
		}
	})
}

// TestWrapUnwrapDEK tests DEK wrapping and unwrapping
func TestWrapUnwrapDEK(t *testing.T) {
	t.Run("Basic wrap/unwrap", func(t *testing.T) {
		kp, _ := GenerateKeyPair()
		dek, _ := GenerateDEK()

		wrapped, err := WrapDEK(dek, kp.PublicKey)
		if err != nil {
			t.Fatalf("WrapDEK() unexpected error: %v", err)
		}

		if wrapped == "" {
			t.Error("Wrapped DEK should not be empty")
		}

		// Verify it's valid base64
		decoded, err := base64.StdEncoding.DecodeString(wrapped)
		if err != nil {
			t.Errorf("Wrapped DEK should be valid base64: %v", err)
		}
		if len(decoded) == 0 {
			t.Error("Decoded wrapped DEK should not be empty")
		}

		unwrapped, err := UnwrapDEK(wrapped, kp.PrivateKey)
		if err != nil {
			t.Fatalf("UnwrapDEK() unexpected error: %v", err)
		}

		if !bytes.Equal(dek, unwrapped) {
			t.Error("Unwrapped DEK should match original")
		}
	})

	t.Run("Invalid DEK size", func(t *testing.T) {
		kp, _ := GenerateKeyPair()
		badDek := []byte("short")

		_, err := WrapDEK(badDek, kp.PublicKey)
		if err == nil {
			t.Error("Should fail with invalid DEK size")
		}
		if !errors.Is(err, ErrInvalidKeyFormat) {
			t.Errorf("Expected ErrInvalidKeyFormat, got %v", err)
		}
	})

	t.Run("Invalid public key", func(t *testing.T) {
		dek, _ := GenerateDEK()

		_, err := WrapDEK(dek, "invalid-key")
		if err == nil {
			t.Error("Should fail with invalid public key")
		}
	})

	t.Run("Invalid private key", func(t *testing.T) {
		kp, _ := GenerateKeyPair()
		dek, _ := GenerateDEK()
		wrapped, _ := WrapDEK(dek, kp.PublicKey)

		_, err := UnwrapDEK(wrapped, "invalid-key")
		if err == nil {
			t.Error("Should fail with invalid private key")
		}
	})

	t.Run("Wrong private key", func(t *testing.T) {
		kp1, _ := GenerateKeyPair()
		kp2, _ := GenerateKeyPair()
		dek, _ := GenerateDEK()

		wrapped, _ := WrapDEK(dek, kp1.PublicKey)
		_, err := UnwrapDEK(wrapped, kp2.PrivateKey)
		if err == nil {
			t.Error("Should fail with wrong private key")
		}
		if !errors.Is(err, ErrDecryptionFailed) {
			t.Errorf("Expected ErrDecryptionFailed, got %v", err)
		}
	})

	t.Run("Tampered wrapped DEK", func(t *testing.T) {
		kp, _ := GenerateKeyPair()
		dek, _ := GenerateDEK()

		wrapped, _ := WrapDEK(dek, kp.PublicKey)
		wrappedBytes, _ := base64.StdEncoding.DecodeString(wrapped)
		wrappedBytes[0] ^= 0xFF
		tampered := base64.StdEncoding.EncodeToString(wrappedBytes)

		_, err := UnwrapDEK(tampered, kp.PrivateKey)
		if err == nil {
			t.Error("Should fail with tampered wrapped DEK")
		}
		if !errors.Is(err, ErrDecryptionFailed) {
			t.Errorf("Expected ErrDecryptionFailed, got %v", err)
		}
	})

	t.Run("Invalid base64", func(t *testing.T) {
		kp, _ := GenerateKeyPair()

		_, err := UnwrapDEK("not-valid-base64!!!", kp.PrivateKey)
		if err == nil {
			t.Error("Should fail with invalid base64")
		}
	})
}

// TestEncryptDecryptPayload tests full payload encryption/decryption
func TestEncryptDecryptPayload(t *testing.T) {
	t.Run("Single recipient", func(t *testing.T) {
		plaintext := []byte("secret message")
		kp, _ := GenerateKeyPair()

		envelope, err := EncryptPayload(plaintext, []string{kp.PublicKey})
		if err != nil {
			t.Fatalf("EncryptPayload() unexpected error: %v", err)
		}

		decrypted, err := DecryptPayload(envelope, kp.PrivateKey)
		if err != nil {
			t.Fatalf("DecryptPayload() unexpected error: %v", err)
		}

		if !bytes.Equal(plaintext, decrypted) {
			t.Errorf("Decrypted payload doesn't match: got %q, want %q", decrypted, plaintext)
		}
	})

	t.Run("Multiple recipients", func(t *testing.T) {
		plaintext := []byte("shared secret")
		kp1, _ := GenerateKeyPair()
		kp2, _ := GenerateKeyPair()
		kp3, _ := GenerateKeyPair()

		envelope, err := EncryptPayload(plaintext, []string{kp1.PublicKey, kp2.PublicKey, kp3.PublicKey})
		if err != nil {
			t.Fatalf("EncryptPayload() unexpected error: %v", err)
		}

		// All recipients should be able to decrypt
		recipients := []*KeyPair{kp1, kp2, kp3}
		for i, kp := range recipients {
			decrypted, err := DecryptPayload(envelope, kp.PrivateKey)
			if err != nil {
				t.Errorf("Recipient %d failed to decrypt: %v", i, err)
				continue
			}
			if !bytes.Equal(plaintext, decrypted) {
				t.Errorf("Recipient %d got wrong plaintext: got %q, want %q", i, decrypted, plaintext)
			}
		}

		// Verify all recipients are stored
		storedRecipients := GetRecipients(envelope)
		if len(storedRecipients) != 3 {
			t.Errorf("Expected 3 recipients, got %d", len(storedRecipients))
		}
	})

	t.Run("Duplicate recipients handled", func(t *testing.T) {
		plaintext := []byte("test")
		kp, _ := GenerateKeyPair()

		// Add same recipient twice
		envelope, err := EncryptPayload(plaintext, []string{kp.PublicKey, kp.PublicKey})
		if err != nil {
			t.Fatalf("EncryptPayload() unexpected error: %v", err)
		}

		if len(envelope.WrappedDEKs) != 1 {
			t.Errorf("Duplicate recipients should be deduplicated, got %d entries", len(envelope.WrappedDEKs))
		}
	})

	t.Run("Empty recipients", func(t *testing.T) {
		_, err := EncryptPayload([]byte("test"), []string{})
		if err == nil {
			t.Error("Should fail with empty recipients")
		}
		if !errors.Is(err, ErrEmptyRecipients) {
			t.Errorf("Expected ErrEmptyRecipients, got %v", err)
		}
	})

	t.Run("Wrong private key", func(t *testing.T) {
		plaintext := []byte("test")
		kp1, _ := GenerateKeyPair()
		kp2, _ := GenerateKeyPair()

		envelope, _ := EncryptPayload(plaintext, []string{kp1.PublicKey})
		_, err := DecryptPayload(envelope, kp2.PrivateKey)
		if err == nil {
			t.Error("Should fail with wrong private key")
		}
		if !errors.Is(err, ErrKeyNotFound) {
			t.Errorf("Expected ErrKeyNotFound, got %v", err)
		}
	})

	t.Run("Tampered envelope ciphertext", func(t *testing.T) {
		plaintext := []byte("test")
		kp, _ := GenerateKeyPair()

		envelope, _ := EncryptPayload(plaintext, []string{kp.PublicKey})

		// Tamper with ciphertext
		envelope.Ciphertext[0] ^= 0xFF
		_, err := DecryptPayload(envelope, kp.PrivateKey)
		if err == nil {
			t.Error("Should detect tampered ciphertext in envelope")
		}
	})

	t.Run("Various plaintext sizes", func(t *testing.T) {
		sizes := []int{0, 1, 16, 256, 1024, 65536}
		kp, _ := GenerateKeyPair()

		for _, size := range sizes {
			plaintext := bytes.Repeat([]byte("A"), size)
			t.Run(fmt.Sprintf("size_%d", size), func(t *testing.T) {
				envelope, err := EncryptPayload(plaintext, []string{kp.PublicKey})
				if err != nil {
					t.Fatalf("Failed to encrypt payload of size %d: %v", size, err)
				}

				decrypted, err := DecryptPayload(envelope, kp.PrivateKey)
				if err != nil {
					t.Fatalf("Failed to decrypt payload of size %d: %v", size, err)
				}

				if !bytes.Equal(plaintext, decrypted) {
					t.Errorf("Mismatch for payload size %d", size)
				}
			})
		}
	})
}

// TestAddRecipient tests adding new recipients to existing envelopes
func TestAddRecipient(t *testing.T) {
	t.Run("Add single recipient", func(t *testing.T) {
		plaintext := []byte("share this")
		owner, _ := GenerateKeyPair()
		collaborator, _ := GenerateKeyPair()

		envelope, _ := EncryptPayload(plaintext, []string{owner.PublicKey})

		err := AddRecipient(envelope, owner.PrivateKey, collaborator.PublicKey)
		if err != nil {
			t.Fatalf("AddRecipient() unexpected error: %v", err)
		}

		// Both should decrypt
		for _, kp := range []*KeyPair{owner, collaborator} {
			decrypted, err := DecryptPayload(envelope, kp.PrivateKey)
			if err != nil {
				t.Errorf("Failed to decrypt for %s: %v", kp.PublicKey[:20], err)
				continue
			}
			if !bytes.Equal(plaintext, decrypted) {
				t.Errorf("Wrong plaintext for %s", kp.PublicKey[:20])
			}
		}
	})

	t.Run("Add duplicate recipient", func(t *testing.T) {
		plaintext := []byte("test")
		owner, _ := GenerateKeyPair()

		envelope, _ := EncryptPayload(plaintext, []string{owner.PublicKey})

		err := AddRecipient(envelope, owner.PrivateKey, owner.PublicKey)
		if err == nil {
			t.Error("Should fail when adding existing recipient")
		}
	})

	t.Run("Add with wrong key", func(t *testing.T) {
		plaintext := []byte("test")
		owner, _ := GenerateKeyPair()
		other, _ := GenerateKeyPair()
		newRecipient, _ := GenerateKeyPair()

		envelope, _ := EncryptPayload(plaintext, []string{owner.PublicKey})

		// Try to add recipient using wrong key
		err := AddRecipient(envelope, other.PrivateKey, newRecipient.PublicKey)
		if err == nil {
			t.Error("Should fail when using wrong private key")
		}
	})

	t.Run("Add multiple recipients", func(t *testing.T) {
		plaintext := []byte("multi-share")
		owner, _ := GenerateKeyPair()
		recipients := make([]*KeyPair, 5)
		for i := 0; i < 5; i++ {
			recipients[i], _ = GenerateKeyPair()
		}

		envelope, _ := EncryptPayload(plaintext, []string{owner.PublicKey})

		for _, recipient := range recipients {
			err := AddRecipient(envelope, owner.PrivateKey, recipient.PublicKey)
			if err != nil {
				t.Fatalf("Failed to add recipient: %v", err)
			}
		}

		// Verify all can decrypt
		allRecipients := append(recipients, owner)
		for i, recipient := range allRecipients {
			decrypted, err := DecryptPayload(envelope, recipient.PrivateKey)
			if err != nil {
				t.Errorf("Recipient %d failed to decrypt: %v", i, err)
				continue
			}
			if !bytes.Equal(plaintext, decrypted) {
				t.Errorf("Recipient %d got wrong plaintext", i)
			}
		}

		// Verify all recipients are stored
		storedRecipients := GetRecipients(envelope)
		if len(storedRecipients) != 6 { // owner + 5 new
			t.Errorf("Expected 6 recipients, got %d", len(storedRecipients))
		}
	})

	t.Run("Payload unchanged after adding recipient", func(t *testing.T) {
		plaintext := []byte("test")
		owner, _ := GenerateKeyPair()
		newRecipient, _ := GenerateKeyPair()

		envelope, _ := EncryptPayload(plaintext, []string{owner.PublicKey})
		originalCiphertext := make([]byte, len(envelope.Ciphertext))
		copy(originalCiphertext, envelope.Ciphertext)

		AddRecipient(envelope, owner.PrivateKey, newRecipient.PublicKey)

		if !bytes.Equal(originalCiphertext, envelope.Ciphertext) {
			t.Error("Ciphertext should not change when adding recipient")
		}
	})
}

// TestRemoveRecipient tests removing recipients
func TestRemoveRecipient(t *testing.T) {
	t.Run("Remove recipient", func(t *testing.T) {
		kp1, _ := GenerateKeyPair()
		kp2, _ := GenerateKeyPair()

		envelope, _ := EncryptPayload([]byte("test"), []string{kp1.PublicKey, kp2.PublicKey})

		err := RemoveRecipient(envelope, kp2.PublicKey)
		if err != nil {
			t.Fatalf("RemoveRecipient() unexpected error: %v", err)
		}

		recipients := GetRecipients(envelope)
		if len(recipients) != 1 {
			t.Errorf("Expected 1 recipient, got %d", len(recipients))
		}

		// Verify remaining recipient can decrypt
		_, err = DecryptPayload(envelope, kp1.PrivateKey)
		if err != nil {
			t.Error("Remaining recipient should still decrypt")
		}

		// Verify removed recipient cannot decrypt
		_, err = DecryptPayload(envelope, kp2.PrivateKey)
		if err == nil {
			t.Error("Removed recipient should not decrypt")
		}
	})

	t.Run("Cannot remove last recipient", func(t *testing.T) {
		kp, _ := GenerateKeyPair()
		envelope, _ := EncryptPayload([]byte("test"), []string{kp.PublicKey})

		err := RemoveRecipient(envelope, kp.PublicKey)
		if err == nil {
			t.Error("Should not allow removing last recipient")
		}
	})
}

// TestVerifyEnvelopeIntegrity tests envelope validation
func TestVerifyEnvelopeIntegrity(t *testing.T) {
	t.Run("Valid envelope", func(t *testing.T) {
		kp, _ := GenerateKeyPair()
		envelope, _ := EncryptPayload([]byte("test"), []string{kp.PublicKey})

		err := VerifyEnvelopeIntegrity(envelope)
		if err != nil {
			t.Errorf("Valid envelope should pass verification: %v", err)
		}
	})

	t.Run("Nil envelope", func(t *testing.T) {
		err := VerifyEnvelopeIntegrity(nil)
		if err == nil {
			t.Error("Should fail on nil envelope")
		}
		if !errors.Is(err, ErrNilEnvelope) {
			t.Errorf("Expected ErrNilEnvelope, got %v", err)
		}
	})

	t.Run("Empty ciphertext", func(t *testing.T) {
		envelope := &Envelope{
			Ciphertext:  []byte{},
			Nonce:       make([]byte, NonceSize),
			WrappedDEKs: map[string]string{"key": "value"},
		}

		err := VerifyEnvelopeIntegrity(envelope)
		if err == nil {
			t.Error("Should fail on empty ciphertext")
		}
		if !errors.Is(err, ErrEmptyCiphertext) {
			t.Errorf("Expected ErrEmptyCiphertext, got %v", err)
		}
	})

	t.Run("Invalid nonce size", func(t *testing.T) {
		envelope := &Envelope{
			Ciphertext:  []byte("data"),
			Nonce:       make([]byte, NonceSize-1),
			WrappedDEKs: map[string]string{"key": "value"},
		}

		err := VerifyEnvelopeIntegrity(envelope)
		if err == nil {
			t.Error("Should fail on invalid nonce size")
		}
		if !errors.Is(err, ErrInvalidNonceSize) {
			t.Errorf("Expected ErrInvalidNonceSize, got %v", err)
		}
	})

	t.Run("No wrapped DEKs", func(t *testing.T) {
		envelope := &Envelope{
			Ciphertext:  []byte("data"),
			Nonce:       make([]byte, NonceSize),
			WrappedDEKs: map[string]string{},
		}

		err := VerifyEnvelopeIntegrity(envelope)
		if err == nil {
			t.Error("Should fail on empty wrapped DEKs")
		}
		if !errors.Is(err, ErrNoWrappedDEKs) {
			t.Errorf("Expected ErrNoWrappedDEKs, got %v", err)
		}
	})

	t.Run("Nil WrappedDEKs map", func(t *testing.T) {
		envelope := &Envelope{
			Ciphertext:  []byte("data"),
			Nonce:       make([]byte, NonceSize),
			WrappedDEKs: nil,
		}

		err := VerifyEnvelopeIntegrity(envelope)
		if err == nil {
			t.Error("Should fail on nil WrappedDEKs")
		}
		if !errors.Is(err, ErrNoWrappedDEKs) {
			t.Errorf("Expected ErrNoWrappedDEKs, got %v", err)
		}
	})
}

// TestGetRecipients tests retrieving recipients from envelope
func TestGetRecipients(t *testing.T) {
	t.Run("Multiple recipients", func(t *testing.T) {
		envelope := &Envelope{
			Ciphertext: []byte("test"),
			Nonce:      make([]byte, NonceSize),
			WrappedDEKs: map[string]string{
				"key1": "wrapped1",
				"key2": "wrapped2",
				"key3": "wrapped3",
			},
		}

		recipients := GetRecipients(envelope)
		if len(recipients) != 3 {
			t.Errorf("Expected 3 recipients, got %d", len(recipients))
		}
	})

	t.Run("Nil envelope", func(t *testing.T) {
		recipients := GetRecipients(nil)
		if recipients != nil {
			t.Error("Should return nil for nil envelope")
		}
	})

	t.Run("Nil WrappedDEKs", func(t *testing.T) {
		envelope := &Envelope{
			Ciphertext:  []byte("test"),
			Nonce:       make([]byte, NonceSize),
			WrappedDEKs: nil,
		}

		recipients := GetRecipients(envelope)
		if recipients != nil {
			t.Error("Should return nil for nil WrappedDEKs")
		}
	})
}

// TestSecurityProperties tests various security requirements
func TestSecurityProperties(t *testing.T) {
	t.Run("No silent garbage on decryption failure", func(t *testing.T) {
		kp, _ := GenerateKeyPair()
		envelope, _ := EncryptPayload([]byte("test"), []string{kp.PublicKey})

		// Test tampering with various parts
		// Tamper ciphertext
		tamperedEnvelope := &Envelope{
			Ciphertext:  make([]byte, len(envelope.Ciphertext)),
			Nonce:       make([]byte, len(envelope.Nonce)),
			WrappedDEKs: envelope.WrappedDEKs,
		}
		copy(tamperedEnvelope.Ciphertext, envelope.Ciphertext)
		copy(tamperedEnvelope.Nonce, envelope.Nonce)
		tamperedEnvelope.Ciphertext[0] ^= 0xFF

		_, err := DecryptPayload(tamperedEnvelope, kp.PrivateKey)
		if err == nil {
			t.Error("Should return error for tampered ciphertext, not garbage data")
		}

		// Tamper nonce
		tamperedEnvelope2 := &Envelope{
			Ciphertext:  make([]byte, len(envelope.Ciphertext)),
			Nonce:       make([]byte, len(envelope.Nonce)),
			WrappedDEKs: envelope.WrappedDEKs,
		}
		copy(tamperedEnvelope2.Ciphertext, envelope.Ciphertext)
		copy(tamperedEnvelope2.Nonce, envelope.Nonce)
		tamperedEnvelope2.Nonce[0] ^= 0xFF

		_, err = DecryptPayload(tamperedEnvelope2, kp.PrivateKey)
		if err == nil {
			t.Error("Should return error for tampered nonce, not garbage data")
		}
	})

	t.Run("Encryption with different DEKs produces different results", func(t *testing.T) {
		plaintext := []byte("test")
		kp, _ := GenerateKeyPair()

		envelope1, _ := EncryptPayload(plaintext, []string{kp.PublicKey})
		envelope2, _ := EncryptPayload(plaintext, []string{kp.PublicKey})

		// Different envelopes should have different ciphertexts (different DEKs and nonces)
		if bytes.Equal(envelope1.Ciphertext, envelope2.Ciphertext) {
			t.Error("Different encryptions should produce different ciphertexts")
		}
	})
}

// TestConcurrentAccess tests concurrent operations
func TestConcurrentAccess(t *testing.T) {
	t.Run("Concurrent encryption", func(t *testing.T) {
		kp, _ := GenerateKeyPair()
		var wg sync.WaitGroup
		errChan := make(chan error, 10)

		for i := 0; i < 10; i++ {
			wg.Add(1)
			go func() {
				defer wg.Done()
				plaintext := []byte("concurrent test")
				_, err := EncryptPayload(plaintext, []string{kp.PublicKey})
				if err != nil {
					errChan <- err
				}
			}()
		}

		wg.Wait()
		close(errChan)

		for err := range errChan {
			t.Errorf("Concurrent encryption failed: %v", err)
		}
	})

	t.Run("Concurrent key generation", func(t *testing.T) {
		var wg sync.WaitGroup
		errChan := make(chan error, 10)

		for i := 0; i < 10; i++ {
			wg.Add(1)
			go func() {
				defer wg.Done()
				_, err := GenerateKeyPair()
				if err != nil {
					errChan <- err
				}
			}()
		}

		wg.Wait()
		close(errChan)

		for err := range errChan {
			t.Errorf("Concurrent key generation failed: %v", err)
		}
	})
}

// TestSecureZeroMemory tests memory zeroing
func TestSecureZeroMemory(t *testing.T) {
	t.Run("Zero memory", func(t *testing.T) {
		data := []byte("sensitive data that needs to be wiped")
		originalLen := len(data)

		secureZeroMemory(data)

		// After zeroing, all bytes should be 0
		for i, b := range data {
			if b != 0 {
				t.Errorf("Byte at position %d should be 0, got %d", i, b)
			}
		}

		// Length should be preserved
		if len(data) != originalLen {
			t.Errorf("Length changed from %d to %d", originalLen, len(data))
		}
	})

	t.Run("Empty slice", func(t *testing.T) {
		// Should not panic
		secureZeroMemory([]byte{})
		secureZeroMemory(nil)
	})
}
