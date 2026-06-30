package app_test

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"

	"github.com/svetlana1959/GophKeeper/cli/internal/app"
	"github.com/svetlana1959/GophKeeper/cli/internal/crypto"
)

// syncBackend is a minimal stand-in for the server: it runs the age challenge
// and stores pushed ciphertext so the reconcile loop can be exercised offline.
type syncBackend struct {
	publicKey      string
	extraDevicePub string // a second account device, if set
	token          string
	nonce          []byte
	secrets        map[string]storedSecret
	seq            int64
}

type storedSecret struct {
	version int
	deleted bool
	seq     int64
	ct      []byte
}

func newSyncBackend() *syncBackend {
	return &syncBackend{token: "session-tok", nonce: []byte("test-nonce"), secrets: map[string]storedSecret{}}
}

func (b *syncBackend) authed(r *http.Request) bool {
	return r.Header.Get("Authorization") == "Bearer "+b.token
}

func (b *syncBackend) handler(t *testing.T) http.Handler {
	mux := http.NewServeMux()

	mux.HandleFunc("POST /devices", func(w http.ResponseWriter, _ *http.Request) {
		respond(w, http.StatusCreated, map[string]any{
			"id": "dev-1", "account_id": "acc-1", "device_name": "d",
			"public_key": b.publicKey, "status": "active",
		})
	})

	mux.HandleFunc("POST /auth/challenge", func(w http.ResponseWriter, _ *http.Request) {
		ct, err := crypto.Engine{}.Seal(b.nonce, []string{b.publicKey})
		if err != nil {
			t.Fatalf("seal: %v", err)
		}
		respond(w, http.StatusOK, map[string]any{
			"challenge":       base64.StdEncoding.EncodeToString(ct),
			"challenge_token": "ch-tok",
		})
	})

	mux.HandleFunc("POST /auth/verify", func(w http.ResponseWriter, r *http.Request) {
		var body struct{ Nonce string }
		_ = json.NewDecoder(r.Body).Decode(&body)
		got, _ := base64.StdEncoding.DecodeString(body.Nonce)
		if !bytes.Equal(got, b.nonce) {
			respond(w, http.StatusUnauthorized, map[string]any{"detail": "bad nonce"})
			return
		}
		respond(w, http.StatusOK, map[string]any{"access_token": b.token, "token_type": "bearer"})
	})

	mux.HandleFunc("POST /sync/push", func(w http.ResponseWriter, r *http.Request) {
		if !b.authed(r) {
			respond(w, http.StatusUnauthorized, map[string]any{"detail": "unauthorized"})
			return
		}
		var body struct {
			Items []struct {
				ID         string `json:"id"`
				Ciphertext string `json:"ciphertext_b64"`
				Deleted    bool   `json:"deleted"`
			} `json:"items"`
		}
		_ = json.NewDecoder(r.Body).Decode(&body)
		var results []map[string]any
		for _, it := range body.Items {
			b.seq++
			ct, _ := base64.StdEncoding.DecodeString(it.Ciphertext)
			ver := 1
			if cur, ok := b.secrets[it.ID]; ok {
				ver = cur.version + 1
			}
			b.secrets[it.ID] = storedSecret{version: ver, deleted: it.Deleted, seq: b.seq, ct: ct}
			results = append(results, map[string]any{"id": it.ID, "status": "applied", "version": ver, "seq": b.seq})
		}
		respond(w, http.StatusOK, map[string]any{"results": results})
	})

	mux.HandleFunc("GET /devices", func(w http.ResponseWriter, r *http.Request) {
		if !b.authed(r) {
			respond(w, http.StatusUnauthorized, map[string]any{"detail": "unauthorized"})
			return
		}
		devices := []map[string]any{
			{"id": "dev-1", "account_id": "acc-1", "device_name": "laptop",
				"public_key": b.publicKey, "status": "active"},
		}
		if b.extraDevicePub != "" {
			devices = append(devices, map[string]any{
				"id": "dev-2", "account_id": "acc-1", "device_name": "phone",
				"public_key": b.extraDevicePub, "status": "active",
			})
		}
		respond(w, http.StatusOK, devices)
	})

	mux.HandleFunc("POST /enroll/invite", func(w http.ResponseWriter, r *http.Request) {
		if !b.authed(r) {
			respond(w, http.StatusUnauthorized, map[string]any{"detail": "unauthorized"})
			return
		}
		respond(w, http.StatusOK, map[string]any{
			"code": "GK-CODE", "expires_at": "2026-07-01T00:00:00Z",
		})
	})

	mux.HandleFunc("POST /enroll/join", func(w http.ResponseWriter, r *http.Request) {
		var body struct {
			DeviceName string `json:"device_name"`
			PublicKey  string `json:"public_key"`
		}
		_ = json.NewDecoder(r.Body).Decode(&body)
		respond(w, http.StatusCreated, map[string]any{
			"id": "dev-joined", "account_id": "acc-1", "device_name": body.DeviceName,
			"public_key": body.PublicKey, "status": "active",
		})
	})

	mux.HandleFunc("GET /sync/changes", func(w http.ResponseWriter, r *http.Request) {
		if !b.authed(r) {
			respond(w, http.StatusUnauthorized, map[string]any{"detail": "unauthorized"})
			return
		}
		since, _ := strconv.ParseInt(r.URL.Query().Get("since"), 10, 64)
		var out []map[string]any
		cursor := since
		for id, s := range b.secrets {
			if s.seq <= since {
				continue
			}
			out = append(out, map[string]any{
				"id": id, "version": s.version, "deleted": s.deleted, "seq": s.seq,
				"updated_at": "2026-07-01T00:00:00Z", "ciphertext_b64": base64.StdEncoding.EncodeToString(s.ct),
			})
			if s.seq > cursor {
				cursor = s.seq
			}
		}
		respond(w, http.StatusOK, map[string]any{"secrets": out, "cursor": cursor})
	})

	return mux
}

func respond(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func TestSync_RegistersAndPushes(t *testing.T) {
	setHome(t)
	be := newSyncBackend()
	srv := httptest.NewServer(be.handler(t))
	defer srv.Close()

	res, err := app.Init(app.InitParams{DeviceName: "laptop", Remote: srv.URL})
	if err != nil {
		t.Fatalf("Init: %v", err)
	}
	be.publicKey = res.PublicKey

	sess, err := app.Open()
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	defer sess.Close()

	mustSet(t, sess, app.SetParams{Name: "a", Value: []byte("1")})
	mustSet(t, sess, app.SetParams{Name: "b", Value: []byte("2")})

	out, err := sess.Sync(context.Background(), "")
	if err != nil {
		t.Fatalf("Sync: %v", err)
	}
	if out.Pushed != 2 || out.Conflicts != 0 {
		t.Fatalf("first sync = %+v, want 2 pushed", out)
	}
	if len(be.secrets) != 2 {
		t.Fatalf("server has %d secrets, want 2", len(be.secrets))
	}

	// A second sync with no local changes pushes nothing.
	out, err = sess.Sync(context.Background(), "")
	if err != nil {
		t.Fatalf("Sync 2: %v", err)
	}
	if out.Pushed != 0 || out.Pulled != 0 {
		t.Fatalf("idempotent sync = %+v, want 0/0", out)
	}

	// An edit re-dirties just that secret.
	mustSet(t, sess, app.SetParams{Name: "a", Value: []byte("1b")})
	out, err = sess.Sync(context.Background(), "")
	if err != nil {
		t.Fatalf("Sync 3: %v", err)
	}
	if out.Pushed != 1 {
		t.Fatalf("after edit = %+v, want 1 pushed", out)
	}
}

func TestSync_PullsRemoteSecret(t *testing.T) {
	setHome(t)
	be := newSyncBackend()
	srv := httptest.NewServer(be.handler(t))
	defer srv.Close()

	res, err := app.Init(app.InitParams{DeviceName: "laptop", Remote: srv.URL})
	if err != nil {
		t.Fatalf("Init: %v", err)
	}
	be.publicKey = res.PublicKey
	// A secret that exists on the server but not locally.
	be.seq++
	be.secrets["remote1"] = storedSecret{version: 1, seq: be.seq, ct: []byte("opaque")}

	sess, err := app.Open()
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	defer sess.Close()

	out, err := sess.Sync(context.Background(), "")
	if err != nil {
		t.Fatalf("Sync: %v", err)
	}
	if out.Pulled != 1 {
		t.Fatalf("sync = %+v, want 1 pulled", out)
	}

	items, err := sess.List("", true)
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	found := false
	for _, it := range items {
		if it.Name == "remote1" {
			found = true
		}
	}
	if !found {
		t.Fatalf("pulled secret not in vault: %+v", items)
	}
}

func TestCreateInvite(t *testing.T) {
	setHome(t)
	be := newSyncBackend()
	srv := httptest.NewServer(be.handler(t))
	defer srv.Close()

	res, err := app.Init(app.InitParams{DeviceName: "laptop", Remote: srv.URL})
	if err != nil {
		t.Fatalf("Init: %v", err)
	}
	be.publicKey = res.PublicKey

	sess, err := app.Open()
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	defer sess.Close()

	inv, err := sess.CreateInvite(context.Background(), "")
	if err != nil {
		t.Fatalf("CreateInvite: %v", err)
	}
	if inv.Code != "GK-CODE" {
		t.Fatalf("invite code = %q, want GK-CODE", inv.Code)
	}
}

func TestListDevices(t *testing.T) {
	setHome(t)
	be := newSyncBackend()
	srv := httptest.NewServer(be.handler(t))
	defer srv.Close()

	res, err := app.Init(app.InitParams{DeviceName: "laptop", Remote: srv.URL})
	if err != nil {
		t.Fatalf("Init: %v", err)
	}
	be.publicKey = res.PublicKey
	other, _ := crypto.GenerateKeyPair()
	be.extraDevicePub = other.Public

	sess, err := app.Open()
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	defer sess.Close()

	devices, err := sess.ListDevices(context.Background(), "")
	if err != nil {
		t.Fatalf("ListDevices: %v", err)
	}
	if len(devices) != 2 {
		t.Fatalf("got %d devices, want 2", len(devices))
	}
	thisCount := 0
	for _, d := range devices {
		if d.This {
			thisCount++
		}
	}
	if thisCount != 1 {
		t.Fatalf("expected exactly one local device, got %d", thisCount)
	}
}

func TestLink(t *testing.T) {
	setHome(t)
	be := newSyncBackend()
	srv := httptest.NewServer(be.handler(t))
	defer srv.Close()

	res, err := app.Init(app.InitParams{DeviceName: "phone", Remote: srv.URL})
	if err != nil {
		t.Fatalf("Init: %v", err)
	}
	be.publicKey = res.PublicKey

	sess, err := app.Open()
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	defer sess.Close()

	if err := sess.Link(context.Background(), "GK-CODE"); err != nil {
		t.Fatalf("Link: %v", err)
	}
	// Already linked now.
	if err := sess.Link(context.Background(), "GK-CODE"); !errors.Is(err, app.ErrAlreadyLinked) {
		t.Fatalf("second Link err = %v, want ErrAlreadyLinked", err)
	}
}

func TestSync_ResharesToAccountDevices(t *testing.T) {
	setHome(t)
	be := newSyncBackend()
	srv := httptest.NewServer(be.handler(t))
	defer srv.Close()

	res, err := app.Init(app.InitParams{DeviceName: "laptop", Remote: srv.URL})
	if err != nil {
		t.Fatalf("Init: %v", err)
	}
	be.publicKey = res.PublicKey
	// A second device in the account (as if freshly linked).
	other, err := crypto.GenerateKeyPair()
	if err != nil {
		t.Fatalf("keypair: %v", err)
	}
	be.extraDevicePub = other.Public

	sess, err := app.Open()
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	defer sess.Close()

	mustSet(t, sess, app.SetParams{Name: "gh", Value: []byte("tok")})

	out, err := sess.Sync(context.Background(), "")
	if err != nil {
		t.Fatalf("Sync: %v", err)
	}
	if out.Reshared < 1 {
		t.Fatalf("sync = %+v, want at least 1 reshared", out)
	}

	// The pushed ciphertext must now be decryptable by the OTHER device.
	if len(be.secrets) != 1 {
		t.Fatalf("server has %d secrets, want 1", len(be.secrets))
	}
	var ct []byte
	for _, s := range be.secrets {
		ct = s.ct
	}
	plain, err := crypto.Engine{}.Open(ct, other.Private)
	if err != nil {
		t.Fatalf("other device cannot decrypt reshared secret: %v", err)
	}
	if !bytes.Contains(plain, []byte("gh")) {
		t.Fatalf("decrypted payload missing name: %s", plain)
	}

	// Once sealed to the full device set, a further sync must not reshare again
	// (guards against the pull-clobbers-recipients ping-pong).
	stable, err := sess.Sync(context.Background(), "")
	if err != nil {
		t.Fatalf("second Sync: %v", err)
	}
	if stable.Reshared != 0 || stable.Pushed != 0 {
		t.Fatalf("second sync = %+v, want 0 reshared / 0 pushed (stable)", stable)
	}
}

func TestSync_PullRecoversNameFromPayload(t *testing.T) {
	setHome(t)
	be := newSyncBackend()
	srv := httptest.NewServer(be.handler(t))
	defer srv.Close()

	res, err := app.Init(app.InitParams{DeviceName: "laptop", Remote: srv.URL})
	if err != nil {
		t.Fatalf("Init: %v", err)
	}
	be.publicKey = res.PublicKey

	// A secret sealed to this device, carrying its name inside the payload, as if
	// it had been created and reshared from another device.
	payload := []byte(`{"name":"github","value":"dG9r"}`) // value = base64("tok")
	sealed, err := crypto.Engine{}.Seal(payload, []string{res.PublicKey})
	if err != nil {
		t.Fatalf("seal: %v", err)
	}
	be.seq++
	be.secrets["sec-xyz"] = storedSecret{version: 1, seq: be.seq, ct: sealed}

	sess, err := app.Open()
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	defer sess.Close()

	if _, err := sess.Sync(context.Background(), ""); err != nil {
		t.Fatalf("Sync: %v", err)
	}

	// The name is recovered from the payload, and the value decrypts.
	got, err := sess.Get("github", "", "")
	if err != nil {
		t.Fatalf("Get by recovered name: %v", err)
	}
	if string(got) != "tok" {
		t.Fatalf("Get = %q, want tok", got)
	}
}
