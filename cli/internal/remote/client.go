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
	ID        string `json:"id"`
	AccountID string `json:"account_id"`
	Name      string `json:"device_name"`
	PublicKey string `json:"public_key"`
	Status    string `json:"status"`
}

// Identity is who the server says the current session belongs to.
type Identity struct {
	DeviceID  string `json:"device_id"`
	AccountID string `json:"account_id"`
}

// Register creates a fresh account owning this device and returns it. The server
// mints the device id. ErrConflict means the public key is already registered.
func (c *Client) Register(ctx context.Context, deviceName, publicKey string) (Device, error) {
	body := map[string]string{"device_name": deviceName, "public_key": publicKey}
	var out Device
	if err := c.do(ctx, http.MethodPost, "/devices", body, &out); err != nil {
		return Device{}, err
	}
	return out, nil
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
