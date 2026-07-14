// Package trust defines the signed certificates that form a GophKeeper account's
// device trust graph: a device vouches for another (admitting it) or revokes one
// (removing it). Certs are signed with a device's Ed25519 key (see internal/crypto)
// and published to the server's append-only trust log, which relays but cannot
// forge them. Each device recomputes the trusted set locally from the verified
// certs; see docs/sync_design.md §11.
package trust

import (
	"crypto/sha256"
	"encoding/base64"
	"errors"
	"strconv"
	"strings"

	"github.com/svetlana1959/GophKeeper/cli/internal/crypto"
)

// Cert kinds.
const (
	KindVouch  = "vouch"
	KindRevoke = "revoke"
)

// ErrUnknownKind is returned for a cert whose Kind is neither vouch nor revoke.
var ErrUnknownKind = errors.New("trust: unknown cert kind")

// Cert is one signed trust statement. A vouch attests the subject's keys and
// admits it; a revoke removes the target. Fields are a discriminated union on
// Kind: vouch uses Subject*, revoke uses Target. Seq is the issuer's monotonic
// counter and PrevHash links the issuer's previous cert, so an issuer's certs
// form a tamper-evident chain. Sig covers every field except itself.
type Cert struct {
	Kind      string `json:"kind"`
	AccountID string `json:"account_id"`
	IssuerID  string `json:"issuer_id"`
	Seq       int64  `json:"seq"`
	PrevHash  string `json:"prev_hash"` // base64 SHA-256 of the issuer's previous cert; "" at seq 0

	// Vouch fields.
	SubjectID      string `json:"subject_id,omitempty"`
	SubjectEncPub  string `json:"subject_enc_pub,omitempty"`
	SubjectSignPub string `json:"subject_sign_pub,omitempty"`

	// Revoke field.
	TargetID string `json:"target_id,omitempty"`

	IssuedAt int64  `json:"issued_at"` // unix seconds
	Sig      string `json:"sig"`       // base64 Ed25519 signature over canonical()
}

// canonical returns the deterministic bytes that Sig signs: a
// domain-separated, field-ordered, newline-delimited encoding. No field can
// contain a newline (UUIDs, base64, and integers do not), so the delimiter is
// unambiguous. Sig itself is excluded.
func (c Cert) canonical() ([]byte, error) {
	var fields []string
	switch c.Kind {
	case KindVouch:
		fields = []string{
			"gophkeeper/trust/vouch/v1",
			c.AccountID,
			c.IssuerID,
			strconv.FormatInt(c.Seq, 10),
			c.PrevHash,
			c.SubjectID,
			c.SubjectEncPub,
			c.SubjectSignPub,
			strconv.FormatInt(c.IssuedAt, 10),
		}
	case KindRevoke:
		fields = []string{
			"gophkeeper/trust/revoke/v1",
			c.AccountID,
			c.IssuerID,
			strconv.FormatInt(c.Seq, 10),
			c.PrevHash,
			c.TargetID,
			strconv.FormatInt(c.IssuedAt, 10),
		}
	default:
		return nil, ErrUnknownKind
	}
	return []byte(strings.Join(fields, "\n")), nil
}

// Sign returns a copy of the cert with Sig set, signed by the issuer's Ed25519
// private key.
func Sign(c Cert, signPrivate string) (Cert, error) {
	msg, err := c.canonical()
	if err != nil {
		return Cert{}, err
	}
	sig, err := crypto.Sign(signPrivate, msg)
	if err != nil {
		return Cert{}, err
	}
	c.Sig = sig
	return c, nil
}

// Verify checks the cert's signature against the issuer's Ed25519 public key.
// It returns crypto.ErrBadSignature on a mismatch and ErrUnknownKind for an
// unrecognized kind.
func (c Cert) Verify(issuerSignPublic string) error {
	msg, err := c.canonical()
	if err != nil {
		return err
	}
	return crypto.Verify(issuerSignPublic, msg, c.Sig)
}

// Hash is the chain link the issuer's next cert carries as PrevHash: a base64
// SHA-256 over the canonical bytes and the signature, so the chain commits to
// both. An unsigned or unknown-kind cert hashes to "".
func (c Cert) Hash() string {
	msg, err := c.canonical()
	if err != nil || c.Sig == "" {
		return ""
	}
	h := sha256.New()
	h.Write(msg)
	h.Write([]byte("\n"))
	h.Write([]byte(c.Sig))
	return base64.RawStdEncoding.EncodeToString(h.Sum(nil))
}
