package trust

import (
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"fmt"
	"strings"
)

// The invite code is the out-of-band secret that bootstraps trust between an
// inviter and a joiner. It never reaches the server — only its hash does — so the
// server can neither forge the inviter's roster nor a joiner's proof. These
// helpers are the MAC layer built on that code; the durable trust artifact issued
// afterwards is a signed vouch Cert. See docs/sync_design.md §11.

// GenerateInviteCode returns a high-entropy, URL-safe pairing code (~192 bits).
func GenerateInviteCode() (string, error) {
	raw := make([]byte, 24)
	if _, err := rand.Read(raw); err != nil {
		return "", fmt.Errorf("trust: generate code: %w", err)
	}
	return base64.RawURLEncoding.EncodeToString(raw), nil
}

// HashCode is the server's opaque handle for a code: hex SHA-256, matching the
// backend's lookup. The server stores and matches only this, never the code.
func HashCode(code string) string {
	sum := sha256.Sum256([]byte(code))
	return hex.EncodeToString(sum[:])
}

// mac is HMAC-SHA256 keyed by the invite code over msg, base64. Only holders of
// the code (inviter and invitee) can compute or verify it; the server cannot.
func mac(code, domain, msg string) string {
	h := hmac.New(sha256.New, []byte(code))
	h.Write([]byte(domain + "\n" + msg))
	return base64.RawStdEncoding.EncodeToString(h.Sum(nil))
}

func deviceBinding(deviceID, encPub, signPub string) string {
	return strings.Join([]string{deviceID, encPub, signPub}, "\n")
}

// JoinMAC binds a joining device's identity to the invite code, proving to the
// inviter (who knows the code) that this exact device redeemed the code it minted.
func JoinMAC(code, deviceID, encPub, signPub string) string {
	return mac(code, "join", deviceBinding(deviceID, encPub, signPub))
}

// VerifyJoinMAC reports whether tag is a valid join MAC for the given identity.
func VerifyJoinMAC(code, deviceID, encPub, signPub, tag string) bool {
	return hmac.Equal([]byte(tag), []byte(JoinMAC(code, deviceID, encPub, signPub)))
}

// RosterEntry is one of the inviter's trusted devices, MAC'd by the code so the
// joiner can adopt it as an anchor without trusting the server.
type RosterEntry struct {
	DeviceID string `json:"device_id"`
	EncPub   string `json:"enc_pub"`
	SignPub  string `json:"sign_pub"`
	Mac      string `json:"mac"`
}

// BuildRoster MACs each trusted device under the code, for the join response.
func BuildRoster(code string, devices []TrustedDevice) []RosterEntry {
	roster := make([]RosterEntry, 0, len(devices))
	for _, d := range devices {
		roster = append(roster, RosterEntry{
			DeviceID: d.DeviceID, EncPub: d.EncPub, SignPub: d.SignPub,
			Mac: mac(code, "roster", deviceBinding(d.DeviceID, d.EncPub, d.SignPub)),
		})
	}
	return roster
}

// VerifiedAnchors returns the roster entries whose MAC checks out under the code,
// as anchors the joiner can trust. A tampered or server-injected entry is dropped.
func VerifiedAnchors(code string, roster []RosterEntry) []Anchor {
	var anchors []Anchor
	for _, e := range roster {
		want := mac(code, "roster", deviceBinding(e.DeviceID, e.EncPub, e.SignPub))
		if hmac.Equal([]byte(e.Mac), []byte(want)) {
			anchors = append(anchors, Anchor{DeviceID: e.DeviceID, EncPub: e.EncPub, SignPub: e.SignPub})
		}
	}
	return anchors
}
