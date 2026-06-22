package crypto

import (
    "bytes"
    "testing"

    "filippo.io/age"
)

func mustIdentity(t *testing.T) age.Identity {
    t.Helper()
    id, err := GenerateIdentity()
    if err != nil {
        t.Fatal(err)
    }
    return id
}

func mustRecipient(t *testing.T, id age.Identity) age.Recipient {
    t.Helper()
    recipient, err := IdentityToRecipient(id)
    if err != nil {
        t.Fatal(err)
    }
    return recipient
}

func TestGenerateIdentityAndRecipient(t *testing.T) {
    id := mustIdentity(t)
    if id == nil {
        t.Fatal("expected identity")
    }
    recipient := mustRecipient(t, id)
    if recipient == nil {
        t.Fatal("expected recipient")
    }
}

func TestEncryptDecryptPayload(t *testing.T) {
    key, err := NewDEK()
    if err != nil {
        t.Fatal(err)
    }
    plaintext := []byte("secret payload")

    ciphertext, nonce, err := EncryptPayload(key, plaintext)
    if err != nil {
        t.Fatal(err)
    }
    if len(ciphertext) == 0 || len(nonce) != 12 {
        t.Fatalf("unexpected ciphertext/nonce sizes: %d / %d", len(ciphertext), len(nonce))
    }

    decrypted, err := DecryptPayload(key, ciphertext, nonce)
    if err != nil {
        t.Fatal(err)
    }
    if !bytes.Equal(decrypted, plaintext) {
        t.Fatalf("decrypted mismatch: got %q, want %q", decrypted, plaintext)
    }

    wrongKey, err := NewDEK()
    if err != nil {
        t.Fatal(err)
    }
    if _, err := DecryptPayload(wrongKey, ciphertext, nonce); err == nil {
        t.Fatal("expected decryption failure with wrong key")
    }

    wrongNonce := append([]byte(nil), nonce...)
    wrongNonce[0] ^= 0xFF
    if _, err := DecryptPayload(key, ciphertext, wrongNonce); err == nil {
        t.Fatal("expected decryption failure with wrong nonce")
    }

    badCiphertext := append([]byte(nil), ciphertext...)
    badCiphertext[0] ^= 0xFF
    if _, err := DecryptPayload(key, badCiphertext, nonce); err == nil {
        t.Fatal("expected decryption failure with tampered ciphertext")
    }
}

func TestWrapUnwrapDEKForMultipleRecipients(t *testing.T) {
    id1 := mustIdentity(t)
    id2 := mustIdentity(t)
    recipient1 := mustRecipient(t, id1)
    recipient2 := mustRecipient(t, id2)

    dek, err := NewDEK()
    if err != nil {
        t.Fatal(err)
    }

    blobs, err := WrapDEK(dek, recipient1, recipient2)
    if err != nil {
        t.Fatal(err)
    }
    if len(blobs) != 2 {
        t.Fatalf("expected 2 wrapped blobs, got %d", len(blobs))
    }

    got1, err := UnwrapDEK(blobs[0], id1)
    if err != nil {
        t.Fatal(err)
    }
    if !bytes.Equal(got1, dek) {
        t.Fatal("unwrapped DEK mismatch for recipient 1")
    }

    got2, err := UnwrapDEK(blobs[1], id2)
    if err != nil {
        t.Fatal(err)
    }
    if !bytes.Equal(got2, dek) {
        t.Fatal("unwrapped DEK mismatch for recipient 2")
    }

    if _, err := UnwrapDEK(blobs[0], id2); err == nil {
        t.Fatal("expected unwrap failure with wrong identity")
    }
}

func TestNewSecretAndAddRecipient(t *testing.T) {
    id1 := mustIdentity(t)
    id2 := mustIdentity(t)
    recipient1 := mustRecipient(t, id1)
    recipient2 := mustRecipient(t, id2)

    plaintext := []byte("very private data")
    secret, err := NewSecret(plaintext, recipient1)
    if err != nil {
        t.Fatal(err)
    }
    if len(secret.EncryptedDEKs) != 1 {
        t.Fatalf("expected 1 encrypted DEK blob, got %d", len(secret.EncryptedDEKs))
    }

    decrypted, err := secret.Decrypt(id1)
    if err != nil {
        t.Fatal(err)
    }
    if !bytes.Equal(decrypted, plaintext) {
        t.Fatal("decrypted payload mismatch for original recipient")
    }

    newDEKs, err := secret.AddRecipient(recipient2, id1)
    if err != nil {
        t.Fatal(err)
    }
    if len(newDEKs) != 2 {
        t.Fatalf("expected 2 encrypted DEK blobs after adding recipient, got %d", len(newDEKs))
    }
    if len(secret.EncryptedDEKs) != 1 {
        t.Fatalf("expected original secret to remain unchanged, got %d blobs", len(secret.EncryptedDEKs))
    }

    upgraded := &Secret{
        EncryptedDEKs: newDEKs,
        Ciphertext:    secret.Ciphertext,
        Nonce:         secret.Nonce,
    }
    decrypted2, err := upgraded.Decrypt(id2)
    if err != nil {
        t.Fatal(err)
    }
    if !bytes.Equal(decrypted2, plaintext) {
        t.Fatal("decrypted payload mismatch for added recipient")
    }
}
