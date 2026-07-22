package remote_test

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/svetlana1959/GophKeeper/cli/internal/crypto"
	"github.com/svetlana1959/GophKeeper/cli/internal/remote"
)

func TestAccount(t *testing.T) {
	kp, _ := crypto.GenerateKeyPair()
	be := newFakeBackend(kp.Public)
	srv := httptest.NewServer(be.handler(t))
	defer srv.Close()

	c := remote.New(srv.URL)
	if err := c.Authenticate(context.Background(), kp.Public, decryptWith(kp.Private)); err != nil {
		t.Fatalf("authenticate: %v", err)
	}

	acc, err := c.Account(context.Background())
	if err != nil {
		t.Fatalf("account: %v", err)
	}
	if acc.ID != "acc-1" || acc.RecoveryPubkey != "age1recovery" {
		t.Errorf("account = %+v, want {acc-1 age1recovery}", acc)
	}
}

func TestInviteProof(t *testing.T) {
	kp, _ := crypto.GenerateKeyPair()
	be := newFakeBackend(kp.Public)
	srv := httptest.NewServer(be.handler(t))
	defer srv.Close()

	c := remote.New(srv.URL)
	if err := c.Authenticate(context.Background(), kp.Public, decryptWith(kp.Private)); err != nil {
		t.Fatalf("authenticate: %v", err)
	}

	proof, err := c.InviteProof(context.Background(), "inv-1")
	if err != nil {
		t.Fatalf("invite proof: %v", err)
	}
	if !proof.Consumed || proof.JoinMAC != "mac-1" || proof.Device.ID != "dev-joined" {
		t.Errorf("proof = %+v, want consumed with dev-joined", proof)
	}
}

func TestAccountAndInviteProofRequireAuth(t *testing.T) {
	c := remote.New("http://unused")
	if _, err := c.Account(context.Background()); !errors.Is(err, remote.ErrNotAuthed) {
		t.Errorf("Account unauthed = %v, want ErrNotAuthed", err)
	}
	if _, err := c.InviteProof(context.Background(), "inv-1"); !errors.Is(err, remote.ErrNotAuthed) {
		t.Errorf("InviteProof unauthed = %v, want ErrNotAuthed", err)
	}
}

func TestAPIError_Error(t *testing.T) {
	withDetail := &remote.APIError{StatusCode: 409, Detail: "already exists"}
	if got := withDetail.Error(); got != "remote: server returned 409: already exists" {
		t.Errorf("Error() = %q", got)
	}
	bare := &remote.APIError{StatusCode: 500}
	if got := bare.Error(); got != "remote: server returned 500" {
		t.Errorf("Error() = %q", got)
	}
}

// A non-2xx with a JSON detail surfaces as an *APIError carrying that detail.
func TestServerErrorSurfacesAsAPIError(t *testing.T) {
	kp, _ := crypto.GenerateKeyPair()
	be := newFakeBackend(kp.Public)
	mux := http.NewServeMux()
	// Auth succeeds, then /accounts/me 500s.
	base := be.handler(t)
	mux.Handle("/api/auth/", base)
	mux.HandleFunc("GET /api/accounts/me", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"detail": "boom"})
	})
	srv := httptest.NewServer(mux)
	defer srv.Close()

	c := remote.New(srv.URL)
	if err := c.Authenticate(context.Background(), kp.Public, decryptWith(kp.Private)); err != nil {
		t.Fatalf("authenticate: %v", err)
	}

	_, err := c.Account(context.Background())
	var apiErr *remote.APIError
	if !errors.As(err, &apiErr) {
		t.Fatalf("err = %v, want *APIError", err)
	}
	if apiErr.StatusCode != 500 || apiErr.Detail != "boom" {
		t.Errorf("apiErr = %+v, want {500 boom}", apiErr)
	}
}
