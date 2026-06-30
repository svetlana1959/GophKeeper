package remote_test

import (
	"bytes"
	"context"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/svetlana1959/GophKeeper/cli/internal/crypto"
	"github.com/svetlana1959/GophKeeper/cli/internal/remote"
)

// fakeBackend stands in for the server: it seals a real age challenge to the
// device key and round-trips the nonce, so the client's auth flow is exercised
// end to end without the Python backend.
type fakeBackend struct {
	publicKey     string
	registerConf  bool   // make /devices answer 409
	unknownDevice bool   // make /auth/challenge answer 401
	nonceByToken  map[string][]byte
	issuedToken   string
}

func newFakeBackend(publicKey string) *fakeBackend {
	return &fakeBackend{publicKey: publicKey, nonceByToken: map[string][]byte{}, issuedToken: "session-xyz"}
}

func (f *fakeBackend) handler(t *testing.T) http.Handler {
	mux := http.NewServeMux()

	mux.HandleFunc("POST /devices", func(w http.ResponseWriter, r *http.Request) {
		if f.registerConf {
			writeJSON(w, http.StatusConflict, map[string]string{"detail": "device already exists"})
			return
		}
		writeJSON(w, http.StatusCreated, remote.Device{
			ID: "dev-1", AccountID: "acc-1", Name: "laptop", PublicKey: f.publicKey, Status: "active",
		})
	})

	mux.HandleFunc("POST /auth/challenge", func(w http.ResponseWriter, r *http.Request) {
		if f.unknownDevice {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"detail": "unknown device"})
			return
		}
		nonce := make([]byte, 32)
		if _, err := rand.Read(nonce); err != nil {
			t.Fatalf("rand: %v", err)
		}
		ciphertext, err := crypto.Engine{}.Seal(nonce, []string{f.publicKey})
		if err != nil {
			t.Fatalf("seal challenge: %v", err)
		}
		token := "challenge-tok"
		f.nonceByToken[token] = nonce
		writeJSON(w, http.StatusOK, map[string]string{
			"challenge":       base64.StdEncoding.EncodeToString(ciphertext),
			"challenge_token": token,
		})
	})

	mux.HandleFunc("POST /auth/verify", func(w http.ResponseWriter, r *http.Request) {
		var body struct {
			ChallengeToken string `json:"challenge_token"`
			Nonce          string `json:"nonce"`
		}
		_ = json.NewDecoder(r.Body).Decode(&body)
		want := f.nonceByToken[body.ChallengeToken]
		got, _ := base64.StdEncoding.DecodeString(body.Nonce)
		if want == nil || !bytes.Equal(want, got) {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"detail": "challenge failed"})
			return
		}
		writeJSON(w, http.StatusOK, map[string]string{
			"access_token": f.issuedToken, "token_type": "bearer",
		})
	})

	mux.HandleFunc("GET /auth/whoami", func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") != "Bearer "+f.issuedToken {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"detail": "missing bearer token"})
			return
		}
		writeJSON(w, http.StatusOK, remote.Identity{DeviceID: "dev-1", AccountID: "acc-1"})
	})

	return mux
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func decryptWith(priv string) remote.DecryptFunc {
	return func(ciphertext []byte) ([]byte, error) {
		return crypto.Engine{}.Open(ciphertext, priv)
	}
}

func TestRegister(t *testing.T) {
	kp, _ := crypto.GenerateKeyPair()
	be := newFakeBackend(kp.Public)
	srv := httptest.NewServer(be.handler(t))
	defer srv.Close()

	dev, err := remote.New(srv.URL).Register(context.Background(), "laptop", kp.Public)
	if err != nil {
		t.Fatalf("register: %v", err)
	}
	if dev.ID == "" || dev.AccountID == "" || dev.PublicKey != kp.Public {
		t.Fatalf("unexpected device: %+v", dev)
	}
}

func TestRegisterConflict(t *testing.T) {
	kp, _ := crypto.GenerateKeyPair()
	be := newFakeBackend(kp.Public)
	be.registerConf = true
	srv := httptest.NewServer(be.handler(t))
	defer srv.Close()

	_, err := remote.New(srv.URL).Register(context.Background(), "laptop", kp.Public)
	if !errors.Is(err, remote.ErrConflict) {
		t.Fatalf("want ErrConflict, got %v", err)
	}
}

func TestAuthenticateAndWhoAmI(t *testing.T) {
	kp, _ := crypto.GenerateKeyPair()
	be := newFakeBackend(kp.Public)
	srv := httptest.NewServer(be.handler(t))
	defer srv.Close()

	c := remote.New(srv.URL)

	// WhoAmI before auth is refused locally, no request made.
	if _, err := c.WhoAmI(context.Background()); !errors.Is(err, remote.ErrNotAuthed) {
		t.Fatalf("want ErrNotAuthed, got %v", err)
	}

	if err := c.Authenticate(context.Background(), kp.Public, decryptWith(kp.Private)); err != nil {
		t.Fatalf("authenticate: %v", err)
	}

	id, err := c.WhoAmI(context.Background())
	if err != nil {
		t.Fatalf("whoami: %v", err)
	}
	if id.DeviceID != "dev-1" || id.AccountID != "acc-1" {
		t.Fatalf("unexpected identity: %+v", id)
	}
}

func TestAuthenticateUnknownDevice(t *testing.T) {
	kp, _ := crypto.GenerateKeyPair()
	be := newFakeBackend(kp.Public)
	be.unknownDevice = true
	srv := httptest.NewServer(be.handler(t))
	defer srv.Close()

	err := remote.New(srv.URL).Authenticate(context.Background(), kp.Public, decryptWith(kp.Private))
	if !errors.Is(err, remote.ErrUnauthorized) {
		t.Fatalf("want ErrUnauthorized, got %v", err)
	}
}
