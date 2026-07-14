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
	"strconv"
	"testing"

	"github.com/svetlana1959/GophKeeper/cli/internal/crypto"
	"github.com/svetlana1959/GophKeeper/cli/internal/remote"
	"github.com/svetlana1959/GophKeeper/cli/internal/trust"
)

// fakeBackend stands in for the server: it seals a real age challenge to the
// device key and round-trips the nonce, so the client's auth flow is exercised
// end to end without the Python backend.
type fakeBackend struct {
	publicKey     string
	unknownDevice bool // make /auth/challenge answer 401
	nonceByToken  map[string][]byte
	issuedToken   string
	secrets       map[string]remote.ChangedSecret
	seq           int64
	certs         []trust.Cert
	certSeq       int64
}

func newFakeBackend(publicKey string) *fakeBackend {
	return &fakeBackend{
		publicKey:    publicKey,
		nonceByToken: map[string][]byte{},
		issuedToken:  "session-xyz",
		secrets:      map[string]remote.ChangedSecret{},
	}
}

func (f *fakeBackend) handler(t *testing.T) http.Handler {
	mux := http.NewServeMux()

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

	mux.HandleFunc("POST /sync/push", func(w http.ResponseWriter, r *http.Request) {
		if !f.authed(r) {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"detail": "unauthorized"})
			return
		}
		var body struct {
			Items []struct {
				ID          string `json:"id"`
				Ciphertext  string `json:"ciphertext_b64"`
				BaseVersion int    `json:"base_version"`
				Deleted     bool   `json:"deleted"`
			} `json:"items"`
		}
		_ = json.NewDecoder(r.Body).Decode(&body)

		var results []map[string]any
		for _, it := range body.Items {
			f.seq++
			ct, _ := base64.StdEncoding.DecodeString(it.Ciphertext)
			existing, ok := f.secrets[it.ID]
			version := 1
			if ok {
				version = existing.Version + 1
			}
			f.secrets[it.ID] = remote.ChangedSecret{
				ID: it.ID, Version: version, Deleted: it.Deleted, Seq: f.seq, Ciphertext: ct,
			}
			results = append(results, map[string]any{
				"id": it.ID, "status": "applied", "version": version, "seq": f.seq,
			})
		}
		writeJSON(w, http.StatusOK, map[string]any{"results": results})
	})

	mux.HandleFunc("GET /sync/changes", func(w http.ResponseWriter, r *http.Request) {
		if !f.authed(r) {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"detail": "unauthorized"})
			return
		}
		since, _ := strconv.ParseInt(r.URL.Query().Get("since"), 10, 64)
		var out []map[string]any
		cursor := since
		for _, s := range f.secrets {
			if s.Seq <= since {
				continue
			}
			out = append(out, map[string]any{
				"id": s.ID, "version": s.Version, "deleted": s.Deleted, "seq": s.Seq,
				"updated_at":     "2026-06-30T00:00:00Z",
				"ciphertext_b64": base64.StdEncoding.EncodeToString(s.Ciphertext),
			})
			if s.Seq > cursor {
				cursor = s.Seq
			}
		}
		writeJSON(w, http.StatusOK, map[string]any{"secrets": out, "cursor": cursor})
	})

	mux.HandleFunc("GET /devices", func(w http.ResponseWriter, r *http.Request) {
		if !f.authed(r) {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"detail": "unauthorized"})
			return
		}
		writeJSON(w, http.StatusOK, []remote.Device{
			{ID: "dev-1", AccountID: "acc-1", Name: "laptop", PublicKey: f.publicKey, Status: "active"},
			{ID: "dev-2", AccountID: "acc-1", Name: "phone", PublicKey: "age1other", Status: "active"},
		})
	})

	mux.HandleFunc("POST /enroll/invite", func(w http.ResponseWriter, r *http.Request) {
		if !f.authed(r) {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"detail": "unauthorized"})
			return
		}
		writeJSON(w, http.StatusOK, map[string]string{
			"code": "GK-TEST-CODE", "expires_at": "2026-07-01T00:00:00Z",
		})
	})

	mux.HandleFunc("POST /enroll/join", func(w http.ResponseWriter, r *http.Request) {
		var body struct {
			Code      string `json:"code"`
			Name      string `json:"device_name"`
			PublicKey string `json:"public_key"`
		}
		_ = json.NewDecoder(r.Body).Decode(&body)
		if body.Code != "GK-TEST-CODE" {
			writeJSON(w, http.StatusBadRequest, map[string]string{"detail": "invalid invite"})
			return
		}
		writeJSON(w, http.StatusCreated, remote.Device{
			ID: "dev-new", AccountID: "acc-1", Name: body.Name, PublicKey: body.PublicKey, Status: "active",
		})
	})

	mux.HandleFunc("POST /trust/certs", func(w http.ResponseWriter, r *http.Request) {
		if !f.authed(r) {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"detail": "unauthorized"})
			return
		}
		var cert trust.Cert
		_ = json.NewDecoder(r.Body).Decode(&cert)
		f.certSeq++
		f.certs = append(f.certs, cert)
		writeJSON(w, http.StatusCreated, cert)
	})

	mux.HandleFunc("GET /trust/certs", func(w http.ResponseWriter, r *http.Request) {
		if !f.authed(r) {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"detail": "unauthorized"})
			return
		}
		since, _ := strconv.ParseInt(r.URL.Query().Get("since"), 10, 64)
		out := f.certs[since:] // fake log cursor is a slice index
		writeJSON(w, http.StatusOK, map[string]any{"certs": out, "cursor": f.certSeq})
	})

	return mux
}

func (f *fakeBackend) authed(r *http.Request) bool {
	return r.Header.Get("Authorization") == "Bearer "+f.issuedToken
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

func TestPushRequiresAuth(t *testing.T) {
	if _, err := remote.New("http://unused").Push(context.Background(), nil); !errors.Is(err, remote.ErrNotAuthed) {
		t.Fatalf("want ErrNotAuthed, got %v", err)
	}
}

func TestPushThenPullRoundTrip(t *testing.T) {
	kp, _ := crypto.GenerateKeyPair()
	be := newFakeBackend(kp.Public)
	srv := httptest.NewServer(be.handler(t))
	defer srv.Close()

	c := remote.New(srv.URL)
	if err := c.Authenticate(context.Background(), kp.Public, decryptWith(kp.Private)); err != nil {
		t.Fatalf("authenticate: %v", err)
	}

	results, err := c.Push(context.Background(), []remote.PushItem{
		{ID: "s1", Ciphertext: []byte("ct-a")},
		{ID: "s2", Ciphertext: []byte("ct-b")},
	})
	if err != nil {
		t.Fatalf("push: %v", err)
	}
	if len(results) != 2 || results[0].Status != "applied" {
		t.Fatalf("unexpected push results: %+v", results)
	}

	secrets, cursor, err := c.Pull(context.Background(), 0)
	if err != nil {
		t.Fatalf("pull: %v", err)
	}
	if len(secrets) != 2 || cursor == 0 {
		t.Fatalf("unexpected pull: secrets=%d cursor=%d", len(secrets), cursor)
	}
	got := map[string][]byte{}
	for _, s := range secrets {
		got[s.ID] = s.Ciphertext
	}
	if string(got["s1"]) != "ct-a" || string(got["s2"]) != "ct-b" {
		t.Fatalf("ciphertext round-trip mismatch: %v", got)
	}

	// A second pull from the cursor sees nothing new.
	more, _, err := c.Pull(context.Background(), cursor)
	if err != nil {
		t.Fatalf("pull 2: %v", err)
	}
	if len(more) != 0 {
		t.Fatalf("expected no new changes, got %d", len(more))
	}
}

func TestListDevices(t *testing.T) {
	kp, _ := crypto.GenerateKeyPair()
	be := newFakeBackend(kp.Public)
	srv := httptest.NewServer(be.handler(t))
	defer srv.Close()

	c := remote.New(srv.URL)
	if err := c.Authenticate(context.Background(), kp.Public, decryptWith(kp.Private)); err != nil {
		t.Fatalf("authenticate: %v", err)
	}
	devices, err := c.ListDevices(context.Background())
	if err != nil {
		t.Fatalf("list devices: %v", err)
	}
	if len(devices) != 2 {
		t.Fatalf("got %d devices, want 2", len(devices))
	}
}

func TestCreateInvite(t *testing.T) {
	kp, _ := crypto.GenerateKeyPair()
	be := newFakeBackend(kp.Public)
	srv := httptest.NewServer(be.handler(t))
	defer srv.Close()

	c := remote.New(srv.URL)
	if err := c.Authenticate(context.Background(), kp.Public, decryptWith(kp.Private)); err != nil {
		t.Fatalf("authenticate: %v", err)
	}
	inv, err := c.CreateInvite(context.Background())
	if err != nil {
		t.Fatalf("create invite: %v", err)
	}
	if inv.Code != "GK-TEST-CODE" || inv.ExpiresAt.IsZero() {
		t.Fatalf("unexpected invite: %+v", inv)
	}
}

func TestJoin(t *testing.T) {
	kp, _ := crypto.GenerateKeyPair()
	be := newFakeBackend(kp.Public)
	srv := httptest.NewServer(be.handler(t))
	defer srv.Close()

	dev, err := remote.New(srv.URL).Join(context.Background(), "GK-TEST-CODE", "phone", kp.Public, "sign-pub")
	if err != nil {
		t.Fatalf("join: %v", err)
	}
	if dev.ID != "dev-new" || dev.PublicKey != kp.Public {
		t.Fatalf("unexpected device: %+v", dev)
	}
}

func TestPublishAndPullTrustCerts(t *testing.T) {
	kp, _ := crypto.GenerateKeyPair()
	be := newFakeBackend(kp.Public)
	srv := httptest.NewServer(be.handler(t))
	defer srv.Close()

	c := remote.New(srv.URL)
	if err := c.Authenticate(context.Background(), kp.Public, decryptWith(kp.Private)); err != nil {
		t.Fatalf("authenticate: %v", err)
	}

	sk, _ := crypto.GenerateSigningKey()
	cert, _ := trust.Sign(trust.Cert{
		Kind: trust.KindVouch, AccountID: "acc-1", IssuerID: "dev-1", Seq: 0,
		SubjectID: "dev-2", SubjectEncPub: "age1other", SubjectSignPub: sk.Public,
		IssuedAt: 1_700_000_000,
	}, sk.Private)

	if err := c.PublishCert(context.Background(), cert); err != nil {
		t.Fatalf("publish cert: %v", err)
	}

	certs, cursor, err := c.TrustChanges(context.Background(), 0)
	if err != nil {
		t.Fatalf("trust changes: %v", err)
	}
	if len(certs) != 1 || cursor != 1 {
		t.Fatalf("got %d certs, cursor %d; want 1, 1", len(certs), cursor)
	}
	// The cert survives the round trip and still verifies under the issuer's key.
	if err := certs[0].Verify(sk.Public); err != nil {
		t.Fatalf("pulled cert does not verify: %v", err)
	}

	// A cursor at the head returns nothing.
	tail, _, err := c.TrustChanges(context.Background(), cursor)
	if err != nil || len(tail) != 0 {
		t.Fatalf("tail = %v, %v; want empty", tail, err)
	}
}

func TestTrustCallsRequireAuth(t *testing.T) {
	if err := remote.New("http://unused").PublishCert(context.Background(), trust.Cert{}); !errors.Is(err, remote.ErrNotAuthed) {
		t.Fatalf("PublishCert unauthed = %v, want ErrNotAuthed", err)
	}
	if _, _, err := remote.New("http://unused").TrustChanges(context.Background(), 0); !errors.Is(err, remote.ErrNotAuthed) {
		t.Fatalf("TrustChanges unauthed = %v, want ErrNotAuthed", err)
	}
}

func TestJoinBadCode(t *testing.T) {
	kp, _ := crypto.GenerateKeyPair()
	be := newFakeBackend(kp.Public)
	srv := httptest.NewServer(be.handler(t))
	defer srv.Close()

	_, err := remote.New(srv.URL).Join(context.Background(), "wrong", "phone", kp.Public, "sign-pub")
	var apiErr *remote.APIError
	if !errors.As(err, &apiErr) || apiErr.StatusCode != http.StatusBadRequest {
		t.Fatalf("want 400 APIError, got %v", err)
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
