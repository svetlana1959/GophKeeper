package app_test

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"

	"github.com/svetlana1959/GophKeeper/cli/internal/app"
	"github.com/svetlana1959/GophKeeper/cli/internal/crypto"
	"github.com/svetlana1959/GophKeeper/cli/internal/remote"
	"github.com/svetlana1959/GophKeeper/cli/internal/trust"
)

// syncBackend is a minimal stand-in for the server: it runs the age challenge
// and stores pushed ciphertext so the reconcile loop can be exercised offline.
type syncBackend struct {
	publicKey      string
	extraDevicePub string // a second account device, if set
	recoveryPubkey string // the account recovery key, if set
	token          string
	nonce          []byte
	secrets        map[string]storedSecret
	seq            int64
	certs          []trust.Cert        // trust log
	roster         []trust.RosterEntry // roster returned on join
	// join proof recorded on POST /enroll/join, served on GET /enroll/invite/{id}
	joinCount  int
	joinedID   string
	joinMac    string
	joinedPub  string
	joinedSign string
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

	mux.HandleFunc("GET /accounts/me", func(w http.ResponseWriter, r *http.Request) {
		if !b.authed(r) {
			respond(w, http.StatusUnauthorized, map[string]any{"detail": "unauthorized"})
			return
		}
		respond(w, http.StatusOK, map[string]any{
			"id": "acc-1", "recovery_pubkey": b.recoveryPubkey,
		})
	})

	mux.HandleFunc("POST /enroll/invite", func(w http.ResponseWriter, r *http.Request) {
		if !b.authed(r) {
			respond(w, http.StatusUnauthorized, map[string]any{"detail": "unauthorized"})
			return
		}
		respond(w, http.StatusOK, map[string]any{
			"invite_id": "inv-1", "expires_at": "2026-07-01T00:00:00Z",
		})
	})

	mux.HandleFunc("POST /enroll/join", func(w http.ResponseWriter, r *http.Request) {
		var body struct {
			DeviceName string `json:"device_name"`
			PublicKey  string `json:"public_key"`
			SignPubKey string `json:"sign_public_key"`
			JoinMac    string `json:"join_mac"`
		}
		_ = json.NewDecoder(r.Body).Decode(&body)
		b.joinCount++
		id := fmt.Sprintf("dev-%d", b.joinCount) // each device gets a distinct id
		b.joinedID = id
		b.joinMac = body.JoinMac
		b.joinedPub = body.PublicKey
		b.joinedSign = body.SignPubKey
		respond(w, http.StatusCreated, map[string]any{
			"device": map[string]any{
				"id": id, "account_id": "acc-1", "device_name": body.DeviceName,
				"public_key": body.PublicKey, "sign_public_key": body.SignPubKey, "status": "active",
			},
			"roster": b.roster,
		})
	})

	mux.HandleFunc("GET /enroll/invite/{id}", func(w http.ResponseWriter, r *http.Request) {
		if !b.authed(r) {
			respond(w, http.StatusUnauthorized, map[string]any{"detail": "unauthorized"})
			return
		}
		respond(w, http.StatusOK, map[string]any{
			"consumed": b.joinedID != "",
			"join_mac": b.joinMac,
			"device": map[string]any{
				"id": b.joinedID, "account_id": "acc-1", "device_name": "phone",
				"public_key": b.joinedPub, "sign_public_key": b.joinedSign, "status": "active",
			},
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

	mux.HandleFunc("GET /trust/certs", func(w http.ResponseWriter, r *http.Request) {
		if !b.authed(r) {
			respond(w, http.StatusUnauthorized, map[string]any{"detail": "unauthorized"})
			return
		}
		// Honor the since cursor like the real backend: certs are 1-indexed by
		// position, so since=N returns everything after the Nth. (A cursor-ignoring
		// stub would make paginated pulls duplicate the log.)
		since := 0
		if v := r.URL.Query().Get("since"); v != "" {
			since, _ = strconv.Atoi(v)
		}
		if since < 0 {
			since = 0
		}
		if since > len(b.certs) {
			since = len(b.certs)
		}
		respond(w, http.StatusOK, map[string]any{"certs": b.certs[since:], "cursor": len(b.certs)})
	})

	mux.HandleFunc("POST /trust/certs", func(w http.ResponseWriter, r *http.Request) {
		if !b.authed(r) {
			respond(w, http.StatusUnauthorized, map[string]any{"detail": "unauthorized"})
			return
		}
		var c trust.Cert
		_ = json.NewDecoder(r.Body).Decode(&c)
		b.certs = append(b.certs, c)
		respond(w, http.StatusCreated, c)
	})

	return mux
}

func respond(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

// mustLink onboards the session onto an account via an invite code, the only way
// a device joins now that the CLI no longer bootstraps accounts.
func mustLink(t *testing.T, sess *app.Session) {
	t.Helper()
	if err := sess.Link(context.Background(), "GK-CODE"); err != nil {
		t.Fatalf("Link: %v", err)
	}
}

func TestSync_PushesAfterLink(t *testing.T) {
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

	mustLink(t, sess)

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

func TestSync_ConcurrentEditForksConflictCopy(t *testing.T) {
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

	mustLink(t, sess)

	// Create and sync "a" (server version 1).
	mustSet(t, sess, app.SetParams{Name: "a", Value: []byte("local-v1")})
	if _, err := sess.Sync(context.Background(), ""); err != nil {
		t.Fatalf("sync 1: %v", err)
	}

	// Another device advances "a" on the server past the version we based on.
	var id string
	for sid := range be.secrets {
		id = sid
	}
	prev := be.secrets[id]
	be.seq++
	be.secrets[id] = storedSecret{version: prev.version + 1, seq: be.seq, ct: []byte("server-wins")}

	// Meanwhile we edit "a" locally without pushing — a genuine concurrent edit.
	mustSet(t, sess, app.SetParams{Name: "a", Value: []byte("local-v2")})

	out, err := sess.Sync(context.Background(), "")
	if err != nil {
		t.Fatalf("sync 2: %v", err)
	}
	if out.Conflicts != 1 {
		t.Fatalf("sync 2 = %+v, want 1 conflict", out)
	}

	// The local edit is preserved as a conflict copy rather than silently lost.
	secs, err := sess.List("", false)
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	var names []string
	conflictFound := false
	for _, s := range secs {
		names = append(names, s.Name)
		if strings.HasPrefix(s.Name, "a (conflict ") {
			conflictFound = true
		}
	}
	if !conflictFound {
		t.Fatalf("no conflict copy created; got %v", names)
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

	mustLink(t, sess)

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

	mustLink(t, sess)

	inv, err := sess.CreateInvite(context.Background(), "")
	if err != nil {
		t.Fatalf("CreateInvite: %v", err)
	}
	// The code is generated locally (never server-made) and non-empty.
	if inv.Code == "" {
		t.Fatal("CreateInvite returned an empty code")
	}
}

func TestSync_SealsSecretsToRecoveryKey(t *testing.T) {
	setHome(t)
	be := newSyncBackend()
	recovery, err := crypto.GenerateKeyPair()
	if err != nil {
		t.Fatalf("GenerateKeyPair: %v", err)
	}
	be.recoveryPubkey = recovery.Public
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

	mustLink(t, sess)

	mustSet(t, sess, app.SetParams{Name: "a", Value: []byte("1")})
	out, err := sess.Sync(context.Background(), "")
	if err != nil {
		t.Fatalf("Sync: %v", err)
	}
	if out.Reshared < 1 {
		t.Fatalf("sync = %+v, want the secret resealed to include the recovery key", out)
	}

	// The pushed ciphertext must be decryptable with the recovery private key —
	// proof it was sealed to the recovery recipient, so an all-devices-lost
	// recovery could read it.
	var ct []byte
	for _, s := range be.secrets {
		ct = s.ct
	}
	if _, err := (crypto.Engine{}).Open(ct, recovery.Private); err != nil {
		t.Fatalf("recovery key cannot decrypt the pushed secret: %v", err)
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

	mustLink(t, sess)

	// ListDevices is read-only and won't bootstrap an account; sync first to bind.
	if _, err := sess.Sync(context.Background(), ""); err != nil {
		t.Fatalf("Sync: %v", err)
	}

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

func TestListDevices_UnlinkedDeviceDoesNotRegister(t *testing.T) {
	setHome(t)
	be := newSyncBackend()
	srv := httptest.NewServer(be.handler(t))
	defer srv.Close()

	if _, err := app.Init(app.InitParams{DeviceName: "laptop", Remote: srv.URL}); err != nil {
		t.Fatalf("Init: %v", err)
	}
	sess, err := app.Open()
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	defer sess.Close()

	// Never synced: a read must not silently create an account server-side.
	if _, err := sess.ListDevices(context.Background(), ""); !errors.Is(err, app.ErrNotLinked) {
		t.Fatalf("ListDevices err = %v, want ErrNotLinked", err)
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

// A device the server merely *reports* (GET /devices) but that no trust cert
// vouches for must never receive plaintext — reshare seals only to the
// cert-derived trusted set. This is the §11 zero-knowledge guarantee: a malicious
// server cannot inject a rogue recipient.
func TestSync_DoesNotSealToUntrustedDevice(t *testing.T) {
	setHome(t)
	be := newSyncBackend()
	srv := httptest.NewServer(be.handler(t))
	defer srv.Close()

	res, err := app.Init(app.InitParams{DeviceName: "laptop", Remote: srv.URL})
	if err != nil {
		t.Fatalf("Init: %v", err)
	}
	be.publicKey = res.PublicKey
	// The server reports a second device, but no vouch cert admits it: it is a
	// stand-in for a server-injected rogue recipient.
	rogue, err := crypto.GenerateKeyPair()
	if err != nil {
		t.Fatalf("keypair: %v", err)
	}
	be.extraDevicePub = rogue.Public

	sess, err := app.Open()
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	defer sess.Close()

	mustLink(t, sess)
	mustSet(t, sess, app.SetParams{Name: "gh", Value: []byte("tok")})

	if _, err := sess.Sync(context.Background(), ""); err != nil {
		t.Fatalf("Sync: %v", err)
	}
	if len(be.secrets) != 1 {
		t.Fatalf("server has %d secrets, want 1", len(be.secrets))
	}
	var ct []byte
	for _, s := range be.secrets {
		ct = s.ct
	}
	// The trusted device (self) can still read it...
	if got, err := sess.Get("gh", "", "value"); err != nil || string(got) != "tok" {
		t.Fatalf("self cannot read own secret: %q, %v", got, err)
	}
	// ...but the untrusted, server-reported device cannot decrypt the pushed ciphertext.
	_, rogueErr := crypto.Engine{}.Open(ct, rogue.Private)
	if !errors.Is(rogueErr, crypto.ErrWrongIdentity) {
		t.Fatalf("rogue device decrypt = %v, want ErrWrongIdentity (not a recipient)", rogueErr)
	}

	// Reshare is stable: with no trust change, a second sync reseals nothing.
	stable, err := sess.Sync(context.Background(), "")
	if err != nil {
		t.Fatalf("second Sync: %v", err)
	}
	if stable.Reshared != 0 || stable.Pushed != 0 {
		t.Fatalf("second sync = %+v, want 0 reshared / 0 pushed (stable)", stable)
	}
}

// The full mesh-forming path: an inviter mints a code-bound invite, a device
// redeems it (real join MAC under the code), and on the inviter's next sync it
// verifies the proof, publishes a vouch cert, and reshares the secret to the
// newly-trusted device — which can then decrypt it.
func TestSync_VouchesForJoinerThenSeals(t *testing.T) {
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

	mustLink(t, sess)
	mustSet(t, sess, app.SetParams{Name: "gh", Value: []byte("tok")})

	// The inviter mints a code-bound invite (pending until redeemed).
	inv, err := sess.CreateInvite(context.Background(), "")
	if err != nil {
		t.Fatalf("CreateInvite: %v", err)
	}

	// A second device redeems it with a real join MAC computed under the code.
	joinerEnc, _ := crypto.GenerateKeyPair()
	joinerSign, _ := crypto.GenerateSigningKey()
	_, _, err = remote.New(srv.URL).Join(
		context.Background(), trust.HashCode(inv.Code), "phone",
		joinerEnc.Public, joinerSign.Public, trust.JoinMAC(inv.Code, joinerEnc.Public, joinerSign.Public),
	)
	if err != nil {
		t.Fatalf("joiner Join: %v", err)
	}

	// The inviter syncs: it should vouch for the joiner and reseal the secret to it.
	if _, err := sess.Sync(context.Background(), ""); err != nil {
		t.Fatalf("Sync: %v", err)
	}

	// A vouch cert for the joiner was published...
	if len(be.certs) != 1 || be.certs[0].Kind != trust.KindVouch || be.certs[0].SubjectID != "dev-2" {
		t.Fatalf("trust log = %+v, want one vouch for dev-2", be.certs)
	}
	// ...and the pushed ciphertext is now decryptable by the joiner.
	var ct []byte
	for _, s := range be.secrets {
		ct = s.ct
	}
	if _, err := (crypto.Engine{}).Open(ct, joinerEnc.Private); err != nil {
		t.Fatalf("joiner cannot decrypt resealed secret: %v", err)
	}
}

// Revoking a joiner publishes a revoke cert; on the next sync reshare rotates the
// secret to exclude it, so the revoked device can no longer decrypt new ciphertext.
func TestRevokeDropsDeviceFromReshare(t *testing.T) {
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

	mustLink(t, sess)
	mustSet(t, sess, app.SetParams{Name: "gh", Value: []byte("tok")})

	// A joiner redeems an invite and gets vouched + sealed in. The server also
	// lists it as dev-2 (so `revoke` can resolve it).
	inv, _ := sess.CreateInvite(context.Background(), "")
	joinerEnc, _ := crypto.GenerateKeyPair()
	joinerSign, _ := crypto.GenerateSigningKey()
	be.extraDevicePub = joinerEnc.Public
	if _, _, err := remote.New(srv.URL).Join(
		context.Background(), trust.HashCode(inv.Code), "phone",
		joinerEnc.Public, joinerSign.Public, trust.JoinMAC(inv.Code, joinerEnc.Public, joinerSign.Public),
	); err != nil {
		t.Fatalf("joiner Join: %v", err)
	}
	if _, err := sess.Sync(context.Background(), ""); err != nil {
		t.Fatalf("first Sync: %v", err)
	}
	// Sanity: the joiner can currently decrypt.
	if _, err := (crypto.Engine{}).Open(currentCiphertext(be), joinerEnc.Private); err != nil {
		t.Fatalf("joiner should decrypt before revoke: %v", err)
	}

	// Revoke the joiner (dev-2), then sync to rotate the secret.
	if err := sess.RevokeDevice(context.Background(), "", "dev-2"); err != nil {
		t.Fatalf("RevokeDevice: %v", err)
	}
	if _, err := sess.Sync(context.Background(), ""); err != nil {
		t.Fatalf("second Sync: %v", err)
	}

	// The log now holds a revoke cert, and the rotated ciphertext excludes the joiner.
	if !hasRevoke(be.certs, "dev-2") {
		t.Fatalf("no revoke cert for dev-2 in log: %+v", be.certs)
	}
	if _, err := (crypto.Engine{}).Open(currentCiphertext(be), joinerEnc.Private); !errors.Is(err, crypto.ErrWrongIdentity) {
		t.Fatalf("revoked joiner decrypt = %v, want ErrWrongIdentity", err)
	}
}

func currentCiphertext(be *syncBackend) []byte {
	for _, s := range be.secrets {
		return s.ct
	}
	return nil
}

func hasRevoke(certs []trust.Cert, target string) bool {
	for _, c := range certs {
		if c.Kind == trust.KindRevoke && c.TargetID == target {
			return true
		}
	}
	return false
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

	mustLink(t, sess)

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
