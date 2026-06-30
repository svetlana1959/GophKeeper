package crypto_test

import (
	"bytes"
	"errors"
	"strings"
	"testing"

	"github.com/svetlana1959/GophKeeper/cli/internal/crypto"
)

// mustKeyPair returns a fresh identity or fails the test.
func mustKeyPair(t testing.TB) crypto.KeyPair {
	t.Helper()
	kp, err := crypto.GenerateKeyPair()
	if err != nil {
		t.Fatalf("GenerateKeyPair: %v", err)
	}
	return kp
}

// mustSeal seals plaintext to recipients or fails the test.
func mustSeal(t testing.TB, plaintext []byte, recipients ...string) []byte {
	t.Helper()
	ct, err := crypto.Engine{}.Seal(plaintext, recipients)
	if err != nil {
		t.Fatalf("Seal: %v", err)
	}
	return ct
}

func TestGenerateKeyPair(t *testing.T) {
	kp := mustKeyPair(t)

	if !strings.HasPrefix(kp.Public, "age1") {
		t.Errorf("Public = %q, want age1 prefix", kp.Public)
	}
	if !strings.HasPrefix(kp.Private, "AGE-SECRET-KEY-1") {
		t.Errorf("Private = %q, want AGE-SECRET-KEY-1 prefix", kp.Private)
	}

	other := mustKeyPair(t)
	if kp.Public == other.Public || kp.Private == other.Private {
		t.Error("successive key pairs should be unique")
	}
}

func TestSealOpen_RoundTrip(t *testing.T) {
	kp := mustKeyPair(t)
	plaintext := []byte("correct horse battery staple")

	ct := mustSeal(t, plaintext, kp.Public)
	if bytes.Contains(ct, plaintext) {
		t.Error("ciphertext should not contain the plaintext")
	}

	got, err := crypto.Engine{}.Open(ct, kp.Private)
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	if !bytes.Equal(got, plaintext) {
		t.Errorf("Open = %q, want %q", got, plaintext)
	}
}

func TestSeal_MultipleRecipients(t *testing.T) {
	plaintext := []byte("shared secret")
	a, b, c := mustKeyPair(t), mustKeyPair(t), mustKeyPair(t)

	ct := mustSeal(t, plaintext, a.Public, b.Public, c.Public)

	for i, kp := range []crypto.KeyPair{a, b, c} {
		got, err := crypto.Engine{}.Open(ct, kp.Private)
		if err != nil {
			t.Fatalf("recipient %d Open: %v", i, err)
		}
		if !bytes.Equal(got, plaintext) {
			t.Errorf("recipient %d got %q, want %q", i, got, plaintext)
		}
	}
}

func TestSeal_NoRecipients(t *testing.T) {
	_, err := crypto.Engine{}.Seal([]byte("x"), nil)
	if !errors.Is(err, crypto.ErrNoRecipients) {
		t.Errorf("err = %v, want ErrNoRecipients", err)
	}
}

func TestSeal_InvalidRecipient(t *testing.T) {
	_, err := crypto.Engine{}.Seal([]byte("x"), []string{"not-an-age-key"})
	if !errors.Is(err, crypto.ErrInvalidKey) {
		t.Errorf("err = %v, want ErrInvalidKey", err)
	}
}

func TestOpen_WrongIdentity(t *testing.T) {
	owner, stranger := mustKeyPair(t), mustKeyPair(t)
	ct := mustSeal(t, []byte("secret"), owner.Public)

	_, err := crypto.Engine{}.Open(ct, stranger.Private)
	if !errors.Is(err, crypto.ErrWrongIdentity) {
		t.Errorf("err = %v, want ErrWrongIdentity", err)
	}
}

func TestOpen_InvalidKey(t *testing.T) {
	kp := mustKeyPair(t)
	ct := mustSeal(t, []byte("secret"), kp.Public)

	_, err := crypto.Engine{}.Open(ct, "not-an-identity")
	if !errors.Is(err, crypto.ErrInvalidKey) {
		t.Errorf("err = %v, want ErrInvalidKey", err)
	}
}

// Tampering must be detected, not silently return garbage. Distinct from
// ErrWrongIdentity, which means "not for this key".
func TestOpen_Tampered(t *testing.T) {
	kp := mustKeyPair(t)
	ct := mustSeal(t, []byte("secret"), kp.Public)

	tampered := bytes.Clone(ct)
	tampered[len(tampered)-1] ^= 0xFF // flip a byte in the payload

	_, err := crypto.Engine{}.Open(tampered, kp.Private)
	if err == nil {
		t.Fatal("expected error for tampered ciphertext")
	}
	if errors.Is(err, crypto.ErrWrongIdentity) {
		t.Errorf("tamper should not be reported as ErrWrongIdentity: %v", err)
	}
}

func TestReshare_AddRecipient(t *testing.T) {
	owner, friend := mustKeyPair(t), mustKeyPair(t)
	plaintext := []byte("share this")
	ct := mustSeal(t, plaintext, owner.Public)

	reshared, err := crypto.Engine{}.Reshare(ct, owner.Private, []string{owner.Public, friend.Public})
	if err != nil {
		t.Fatalf("Reshare: %v", err)
	}

	for name, kp := range map[string]crypto.KeyPair{"owner": owner, "friend": friend} {
		got, err := crypto.Engine{}.Open(reshared, kp.Private)
		if err != nil {
			t.Fatalf("%s Open after reshare: %v", name, err)
		}
		if !bytes.Equal(got, plaintext) {
			t.Errorf("%s got %q, want %q", name, got, plaintext)
		}
	}
}

// Removing a recipient via Reshare must actually revoke access to the new
// ciphertext — the key is rotated, not just the header entry dropped.
func TestReshare_RemoveRecipient(t *testing.T) {
	owner, removed := mustKeyPair(t), mustKeyPair(t)
	plaintext := []byte("private now")
	ct := mustSeal(t, plaintext, owner.Public, removed.Public)

	reshared, err := crypto.Engine{}.Reshare(ct, owner.Private, []string{owner.Public})
	if err != nil {
		t.Fatalf("Reshare: %v", err)
	}

	if _, err := (crypto.Engine{}).Open(reshared, owner.Private); err != nil {
		t.Errorf("owner should still Open: %v", err)
	}
	if _, err := (crypto.Engine{}).Open(reshared, removed.Private); !errors.Is(err, crypto.ErrWrongIdentity) {
		t.Errorf("removed recipient err = %v, want ErrWrongIdentity", err)
	}
}

func TestReshare_WrongIdentity(t *testing.T) {
	owner, stranger, target := mustKeyPair(t), mustKeyPair(t), mustKeyPair(t)
	ct := mustSeal(t, []byte("secret"), owner.Public)

	_, err := crypto.Engine{}.Reshare(ct, stranger.Private, []string{owner.Public, target.Public})
	if !errors.Is(err, crypto.ErrWrongIdentity) {
		t.Errorf("err = %v, want ErrWrongIdentity", err)
	}
}

func TestSeal_DistinctCiphertexts(t *testing.T) {
	kp := mustKeyPair(t)
	plaintext := []byte("same input")

	if bytes.Equal(mustSeal(t, plaintext, kp.Public), mustSeal(t, plaintext, kp.Public)) {
		t.Error("sealing the same plaintext twice should yield different ciphertexts")
	}
}

// FuzzSealOpen is the core property: Open(Seal(x)) == x for any plaintext.
func FuzzSealOpen(f *testing.F) {
	kp := mustKeyPair(f)
	for _, seed := range [][]byte{nil, {}, []byte("hello"), bytes.Repeat([]byte("A"), 4096)} {
		f.Add(seed)
	}

	f.Fuzz(func(t *testing.T, plaintext []byte) {
		ct, err := crypto.Engine{}.Seal(plaintext, []string{kp.Public})
		if err != nil {
			t.Fatalf("Seal: %v", err)
		}
		got, err := crypto.Engine{}.Open(ct, kp.Private)
		if err != nil {
			t.Fatalf("Open: %v", err)
		}
		if !bytes.Equal(got, plaintext) {
			t.Fatalf("round-trip mismatch: got %q, want %q", got, plaintext)
		}
	})
}
