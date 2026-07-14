package trust_test

import (
	"crypto/sha256"
	"encoding/hex"
	"testing"

	"github.com/svetlana1959/GophKeeper/cli/internal/trust"
)

func TestGenerateInviteCodeIsUnique(t *testing.T) {
	a, err := trust.GenerateInviteCode()
	if err != nil {
		t.Fatalf("GenerateInviteCode: %v", err)
	}
	b, _ := trust.GenerateInviteCode()
	if a == b || a == "" {
		t.Fatalf("codes not unique/non-empty: %q %q", a, b)
	}
}

func TestHashCodeMatchesServerScheme(t *testing.T) {
	// The backend uses hex(sha256(code)); the client must match for lookup.
	code := "some-code"
	sum := sha256.Sum256([]byte(code))
	if got, want := trust.HashCode(code), hex.EncodeToString(sum[:]); got != want {
		t.Fatalf("HashCode = %q, want %q", got, want)
	}
}

func TestJoinMACRoundTrip(t *testing.T) {
	code := "code-abc"
	tag := trust.JoinMAC(code, "dev-2", "age1-2", "sign-2")

	if !trust.VerifyJoinMAC(code, "dev-2", "age1-2", "sign-2", tag) {
		t.Fatal("valid join MAC did not verify")
	}
	// Wrong code, wrong identity, and a swapped key all fail.
	if trust.VerifyJoinMAC("other", "dev-2", "age1-2", "sign-2", tag) {
		t.Fatal("join MAC verified under the wrong code")
	}
	if trust.VerifyJoinMAC(code, "dev-2", "age1-ATTACKER", "sign-2", tag) {
		t.Fatal("join MAC verified with a swapped enc key")
	}
}

func TestRosterRoundTrip(t *testing.T) {
	code := "code-xyz"
	devs := []trust.TrustedDevice{
		{DeviceID: "root", EncPub: "age1-root", SignPub: "sign-root"},
		{DeviceID: "a", EncPub: "age1-a", SignPub: "sign-a"},
	}
	roster := trust.BuildRoster(code, devs)

	anchors := trust.VerifiedAnchors(code, roster)
	if len(anchors) != 2 {
		t.Fatalf("verified %d anchors, want 2", len(anchors))
	}
	// Anchors carry the keys through unchanged.
	if anchors[0].SignPub != "sign-root" || anchors[0].EncPub != "age1-root" {
		t.Fatalf("anchor keys not carried: %+v", anchors[0])
	}
}

func TestRosterRejectsTamperingAndWrongCode(t *testing.T) {
	code := "code-xyz"
	roster := trust.BuildRoster(code, []trust.TrustedDevice{
		{DeviceID: "root", EncPub: "age1-root", SignPub: "sign-root"},
	})

	// A server that swaps in a rogue key but cannot recompute the MAC is dropped.
	tampered := make([]trust.RosterEntry, len(roster))
	copy(tampered, roster)
	tampered[0].EncPub = "age1-rogue"
	if len(trust.VerifiedAnchors(code, tampered)) != 0 {
		t.Fatal("tampered roster entry was accepted")
	}
	// Without the code, no entry verifies.
	if len(trust.VerifiedAnchors("wrong-code", roster)) != 0 {
		t.Fatal("roster verified under the wrong code")
	}
}
