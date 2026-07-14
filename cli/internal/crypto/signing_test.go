package crypto_test

import (
	"errors"
	"testing"

	"github.com/svetlana1959/GophKeeper/cli/internal/crypto"
)

func TestSignVerifyRoundTrip(t *testing.T) {
	kp, err := crypto.GenerateSigningKey()
	if err != nil {
		t.Fatalf("GenerateSigningKey: %v", err)
	}

	msg := []byte("vouch: device-b enc_pub sign_pub")
	sig, err := crypto.Sign(kp.Private, msg)
	if err != nil {
		t.Fatalf("Sign: %v", err)
	}
	if err := crypto.Verify(kp.Public, msg, sig); err != nil {
		t.Fatalf("Verify: %v", err)
	}
}

func TestVerifyRejectsTamperedMessage(t *testing.T) {
	kp, _ := crypto.GenerateSigningKey()
	sig, _ := crypto.Sign(kp.Private, []byte("original"))

	if err := crypto.Verify(kp.Public, []byte("tampered"), sig); !errors.Is(err, crypto.ErrBadSignature) {
		t.Fatalf("Verify tampered = %v, want ErrBadSignature", err)
	}
}

func TestVerifyRejectsWrongKey(t *testing.T) {
	signer, _ := crypto.GenerateSigningKey()
	other, _ := crypto.GenerateSigningKey()
	msg := []byte("payload")
	sig, _ := crypto.Sign(signer.Private, msg)

	if err := crypto.Verify(other.Public, msg, sig); !errors.Is(err, crypto.ErrBadSignature) {
		t.Fatalf("Verify wrong key = %v, want ErrBadSignature", err)
	}
}

func TestSignRejectsInvalidPrivateKey(t *testing.T) {
	if _, err := crypto.Sign("not-base64!!", []byte("x")); !errors.Is(err, crypto.ErrInvalidKey) {
		t.Fatalf("Sign bad key = %v, want ErrInvalidKey", err)
	}
	// Valid base64 but wrong length.
	if _, err := crypto.Sign("YWJj", []byte("x")); !errors.Is(err, crypto.ErrInvalidKey) {
		t.Fatalf("Sign short key = %v, want ErrInvalidKey", err)
	}
}

func TestVerifyRejectsInvalidInputs(t *testing.T) {
	kp, _ := crypto.GenerateSigningKey()
	sig, _ := crypto.Sign(kp.Private, []byte("x"))

	if err := crypto.Verify("bad!!", []byte("x"), sig); !errors.Is(err, crypto.ErrInvalidKey) {
		t.Fatalf("Verify bad pub = %v, want ErrInvalidKey", err)
	}
	if err := crypto.Verify(kp.Public, []byte("x"), "bad!!"); !errors.Is(err, crypto.ErrInvalidKey) {
		t.Fatalf("Verify bad sig encoding = %v, want ErrInvalidKey", err)
	}
}
