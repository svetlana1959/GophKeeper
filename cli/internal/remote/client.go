package remote

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/svetlana1959/GophKeeper/cli/internal/trust"
)

// DecryptFunc decrypts a challenge ciphertext with the device's private key,
// returning the nonce. The caller (the app layer) owns the key; this package
// never sees it.
type DecryptFunc func(ciphertext []byte) (nonce []byte, err error)

// Sentinel errors callers can match with errors.Is. Anything else surfaces as
// an *APIError carrying the status code.
var (
	ErrUnauthorized = errors.New("remote: unauthorized")
	ErrConflict     = errors.New("remote: already exists")
	ErrNotAuthed    = errors.New("remote: client is not authenticated")
)

// APIError is an unexpected non-2xx response, carrying the server's detail.
type APIError struct {
	StatusCode int
	Detail     string
}

func (e *APIError) Error() string {
	if e.Detail != "" {
		return fmt.Sprintf("remote: server returned %d: %s", e.StatusCode, e.Detail)
	}
	return fmt.Sprintf("remote: server returned %d", e.StatusCode)
}

// Client talks to one GophKeeper backend. After Authenticate succeeds it holds a
// session token used to authorize subsequent calls. It is not safe for
// concurrent use across an Authenticate.
type Client struct {
	baseURL string
	http    *http.Client
	token   string
}

// New builds a client for baseURL (trailing slash optional).
func New(baseURL string) *Client {
	return &Client{
		baseURL: strings.TrimRight(baseURL, "/"),
		http:    &http.Client{Timeout: 30 * time.Second},
	}
}

// Device is a registered device as the server reports it.
type Device struct {
	ID            string `json:"id"`
	AccountID     string `json:"account_id"`
	Name          string `json:"device_name"`
	PublicKey     string `json:"public_key"`
	SignPublicKey string `json:"sign_public_key"`
	Status        string `json:"status"`
}

// Identity is who the server says the current session belongs to.
type Identity struct {
	DeviceID  string `json:"device_id"`
	AccountID string `json:"account_id"`
}

// Authenticate runs the age challenge/response and stores the resulting session
// token on the client. decrypt recovers the nonce from the challenge ciphertext.
// ErrUnauthorized means the device is unknown or revoked.
func (c *Client) Authenticate(ctx context.Context, publicKey string, decrypt DecryptFunc) error {
	var ch struct {
		Challenge      string `json:"challenge"`
		ChallengeToken string `json:"challenge_token"`
	}
	if err := c.do(ctx, http.MethodPost, "/auth/challenge",
		map[string]string{"public_key": publicKey}, &ch); err != nil {
		return err
	}

	ciphertext, err := base64.StdEncoding.DecodeString(ch.Challenge)
	if err != nil {
		return fmt.Errorf("remote: decode challenge: %w", err)
	}
	nonce, err := decrypt(ciphertext)
	if err != nil {
		return fmt.Errorf("remote: answer challenge: %w", err)
	}

	var session struct {
		AccessToken string `json:"access_token"`
	}
	verify := map[string]string{
		"challenge_token": ch.ChallengeToken,
		"nonce":           base64.StdEncoding.EncodeToString(nonce),
	}
	if err := c.do(ctx, http.MethodPost, "/auth/verify", verify, &session); err != nil {
		return err
	}
	c.token = session.AccessToken
	return nil
}

// WhoAmI returns the authenticated device identity. Requires a prior
// Authenticate (else ErrNotAuthed).
func (c *Client) WhoAmI(ctx context.Context) (Identity, error) {
	if c.token == "" {
		return Identity{}, ErrNotAuthed
	}
	var id Identity
	if err := c.do(ctx, http.MethodGet, "/auth/whoami", nil, &id); err != nil {
		return Identity{}, err
	}
	return id, nil
}

// PushItem is one local change to upload. BaseVersion is the server version the
// client last reconciled (0 for a never-synced secret). Ciphertext may be empty
// when Deleted is set. Recipients are the age public keys the secret is sealed
// to, so the server can scope who may pull it.
type PushItem struct {
	ID          string
	Ciphertext  []byte
	BaseVersion int
	Deleted     bool
	Recipients  []string
}

// PushResult is the server's per-item verdict. Status is "applied" or
// "conflict"; on conflict Version is the winning server version to reconcile to.
type PushResult struct {
	ID      string
	Status  string
	Version int
	Seq     int64
}

// ChangedSecret is one secret in a pull delta (tombstones included).
type ChangedSecret struct {
	ID         string
	Version    int
	Deleted    bool
	Seq        int64
	Ciphertext []byte
}

// Push uploads a batch of changes and returns the per-item results. Requires a
// prior Authenticate.
func (c *Client) Push(ctx context.Context, items []PushItem) ([]PushResult, error) {
	if c.token == "" {
		return nil, ErrNotAuthed
	}

	type wireItem struct {
		ID          string   `json:"id"`
		Ciphertext  string   `json:"ciphertext_b64"`
		BaseVersion int      `json:"base_version"`
		Deleted     bool     `json:"deleted"`
		Recipients  []string `json:"recipients"`
	}
	wire := make([]wireItem, len(items))
	for i, it := range items {
		recipients := it.Recipients
		if recipients == nil {
			recipients = []string{}
		}
		wire[i] = wireItem{
			ID:          it.ID,
			Ciphertext:  base64.StdEncoding.EncodeToString(it.Ciphertext),
			BaseVersion: it.BaseVersion,
			Deleted:     it.Deleted,
			Recipients:  recipients,
		}
	}

	var resp struct {
		Results []struct {
			ID      string `json:"id"`
			Status  string `json:"status"`
			Version int    `json:"version"`
			Seq     int64  `json:"seq"`
		} `json:"results"`
	}
	if err := c.do(ctx, http.MethodPost, "/sync/push", map[string]any{"items": wire}, &resp); err != nil {
		return nil, err
	}

	out := make([]PushResult, len(resp.Results))
	for i, r := range resp.Results {
		out[i] = PushResult{ID: r.ID, Status: r.Status, Version: r.Version, Seq: r.Seq}
	}
	return out, nil
}

// Pull fetches the account's changes with seq greater than since, returning them
// in seq order along with the new cursor. Requires a prior Authenticate.
func (c *Client) Pull(ctx context.Context, since int64) ([]ChangedSecret, int64, error) {
	if c.token == "" {
		return nil, 0, ErrNotAuthed
	}

	var resp struct {
		Secrets []struct {
			ID         string `json:"id"`
			Version    int    `json:"version"`
			Deleted    bool   `json:"deleted"`
			Seq        int64  `json:"seq"`
			Ciphertext string `json:"ciphertext_b64"`
		} `json:"secrets"`
		Cursor int64 `json:"cursor"`
	}
	path := fmt.Sprintf("/sync/changes?since=%d", since)
	if err := c.do(ctx, http.MethodGet, path, nil, &resp); err != nil {
		return nil, 0, err
	}

	out := make([]ChangedSecret, len(resp.Secrets))
	for i, s := range resp.Secrets {
		ciphertext, err := base64.StdEncoding.DecodeString(s.Ciphertext)
		if err != nil {
			return nil, 0, fmt.Errorf("remote: decode secret %s: %w", s.ID, err)
		}
		out[i] = ChangedSecret{
			ID: s.ID, Version: s.Version, Deleted: s.Deleted, Seq: s.Seq, Ciphertext: ciphertext,
		}
	}
	return out, resp.Cursor, nil
}

// ListDevices returns the account's devices. Requires a prior Authenticate.
func (c *Client) ListDevices(ctx context.Context) ([]Device, error) {
	if c.token == "" {
		return nil, ErrNotAuthed
	}
	var devices []Device
	if err := c.do(ctx, http.MethodGet, "/devices", nil, &devices); err != nil {
		return nil, err
	}
	return devices, nil
}

// Account is the caller's account as reported by the server.
type Account struct {
	ID             string `json:"id"`
	RecoveryPubkey string `json:"recovery_pubkey"` // "" when no recovery key is set
}

// Account returns the caller's account (including its recovery public key, if
// set). Requires a prior Authenticate.
func (c *Client) Account(ctx context.Context) (Account, error) {
	if c.token == "" {
		return Account{}, ErrNotAuthed
	}
	var acc Account
	if err := c.do(ctx, http.MethodGet, "/accounts/me", nil, &acc); err != nil {
		return Account{}, err
	}
	return acc, nil
}

// PublishCert appends one signed trust cert to the account's trust log. The
// server relays it without verifying the signature. ErrConflict means the cert's
// seq is not the next in this device's chain (re-pull the log and re-issue).
// Requires a prior Authenticate.
func (c *Client) PublishCert(ctx context.Context, cert trust.Cert) error {
	if c.token == "" {
		return ErrNotAuthed
	}
	return c.do(ctx, http.MethodPost, "/trust/certs", cert, nil)
}

// TrustChanges pulls the account's trust certs with log cursor greater than
// since, in order, along with the new cursor. The caller verifies each cert's
// signature and chain. Requires a prior Authenticate.
func (c *Client) TrustChanges(ctx context.Context, since int64) ([]trust.Cert, int64, error) {
	if c.token == "" {
		return nil, 0, ErrNotAuthed
	}
	var resp struct {
		Certs  []trust.Cert `json:"certs"`
		Cursor int64        `json:"cursor"`
	}
	path := fmt.Sprintf("/trust/certs?since=%d", since)
	if err := c.do(ctx, http.MethodGet, path, nil, &resp); err != nil {
		return nil, 0, err
	}
	return resp.Certs, resp.Cursor, nil
}

// Invite is a single-use pairing code for linking a new device.
type Invite struct {
	Code      string    `json:"code"`
	ExpiresAt time.Time `json:"expires_at"`
}

// CreateInvite mints a pairing code for a new device to join this account.
// Requires a prior Authenticate.
func (c *Client) CreateInvite(ctx context.Context) (Invite, error) {
	if c.token == "" {
		return Invite{}, ErrNotAuthed
	}
	var inv Invite
	if err := c.do(ctx, http.MethodPost, "/enroll/invite", nil, &inv); err != nil {
		return Invite{}, err
	}
	return inv, nil
}

// Join links this device into an account using a pairing code. It is
// unauthenticated — the code is the authorization. ErrConflict means the public
// key is already registered. signPublicKey is the device's Ed25519 trust key.
func (c *Client) Join(
	ctx context.Context, code, deviceName, publicKey, signPublicKey string,
) (Device, error) {
	body := map[string]string{
		"code": code, "device_name": deviceName,
		"public_key": publicKey, "sign_public_key": signPublicKey,
	}
	var dev Device
	if err := c.do(ctx, http.MethodPost, "/enroll/join", body, &dev); err != nil {
		return Device{}, err
	}
	return dev, nil
}

// do performs a request, encoding body as JSON (when non-nil), attaching the
// bearer token (when set), and decoding a 2xx response into out (when non-nil).
func (c *Client) do(ctx context.Context, method, path string, body, out any) error {
	var reader io.Reader
	if body != nil {
		encoded, err := json.Marshal(body)
		if err != nil {
			return fmt.Errorf("remote: encode request: %w", err)
		}
		reader = bytes.NewReader(encoded)
	}

	req, err := http.NewRequestWithContext(ctx, method, c.baseURL+path, reader)
	if err != nil {
		return fmt.Errorf("remote: build request: %w", err)
	}
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	if c.token != "" {
		req.Header.Set("Authorization", "Bearer "+c.token)
	}

	resp, err := c.http.Do(req)
	if err != nil {
		return fmt.Errorf("remote: %s %s: %w", method, path, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return statusError(resp)
	}
	if out == nil {
		return nil
	}
	if err := json.NewDecoder(resp.Body).Decode(out); err != nil {
		return fmt.Errorf("remote: decode response: %w", err)
	}
	return nil
}

// statusError reads the server's {"detail": ...} body and maps the status to a
// sentinel where one fits, or an *APIError otherwise.
func statusError(resp *http.Response) error {
	var payload struct {
		Detail string `json:"detail"`
	}
	if raw, _ := io.ReadAll(resp.Body); len(raw) > 0 {
		_ = json.Unmarshal(raw, &payload)
	}
	switch resp.StatusCode {
	case http.StatusUnauthorized:
		return fmt.Errorf("%w: %s", ErrUnauthorized, payload.Detail)
	case http.StatusConflict:
		return fmt.Errorf("%w: %s", ErrConflict, payload.Detail)
	default:
		return &APIError{StatusCode: resp.StatusCode, Detail: payload.Detail}
	}
}
