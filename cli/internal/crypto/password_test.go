package crypto_test

import (
	"bytes"
	"errors"
	"testing"

	"github.com/svetlana1959/GophKeeper/cli/internal/crypto"
)

func TestPassword_RoundTrip(t *testing.T) {
	secret := []byte("AGE-SECRET-KEY-1EXAMPLE")

	sealed, err := crypto.SealWithPassword(secret, "1234")
	if err != nil {
		t.Fatalf("SealWithPassword: %v", err)
	}
	if bytes.Contains(sealed, secret) {
		t.Error("sealed output should not contain the plaintext")
	}

	got, err := crypto.OpenWithPassword(sealed, "1234")
	if err != nil {
		t.Fatalf("OpenWithPassword: %v", err)
	}
	if !bytes.Equal(got, secret) {
		t.Errorf("round trip = %q, want %q", got, secret)
	}
}

func TestPassword_WrongPIN(t *testing.T) {
	sealed, err := crypto.SealWithPassword([]byte("key"), "1234")
	if err != nil {
		t.Fatalf("SealWithPassword: %v", err)
	}

	if _, err := crypto.OpenWithPassword(sealed, "9999"); !errors.Is(err, crypto.ErrWrongPassword) {
		t.Errorf("err = %v, want ErrWrongPassword", err)
	}
}
