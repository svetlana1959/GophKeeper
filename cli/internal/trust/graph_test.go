package trust_test

import (
	"sort"
	"testing"

	"github.com/svetlana1959/GophKeeper/cli/internal/crypto"
	"github.com/svetlana1959/GophKeeper/cli/internal/trust"
)

// dev is a test device with its own signing key.
type dev struct {
	id   string
	enc  string
	sign crypto.SigningKeyPair
}

func newDev(id string) dev {
	sk, _ := crypto.GenerateSigningKey()
	return dev{id: id, enc: "age1-" + id, sign: sk}
}

func (d dev) anchor() trust.Anchor {
	return trust.Anchor{DeviceID: d.id, EncPub: d.enc, SignPub: d.sign.Public}
}

// vouchFor: issuer signs a vouch admitting subject.
func vouchFor(t *testing.T, issuer, subject dev) trust.Cert {
	t.Helper()
	c, err := trust.Sign(trust.Cert{
		Kind: trust.KindVouch, AccountID: "acct", IssuerID: issuer.id,
		SubjectID: subject.id, SubjectEncPub: subject.enc, SubjectSignPub: subject.sign.Public,
	}, issuer.sign.Private)
	if err != nil {
		t.Fatalf("sign vouch: %v", err)
	}
	return c
}

// revokeOf: issuer signs a revoke of target.
func revokeOf(t *testing.T, issuer, target dev) trust.Cert {
	t.Helper()
	c, err := trust.Sign(trust.Cert{
		Kind: trust.KindRevoke, AccountID: "acct", IssuerID: issuer.id, TargetID: target.id,
	}, issuer.sign.Private)
	if err != nil {
		t.Fatalf("sign revoke: %v", err)
	}
	return c
}

func trustedIDs(m map[string]trust.TrustedDevice) []string {
	ids := make([]string, 0, len(m))
	for id := range m {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	return ids
}

func assertTrusted(t *testing.T, got map[string]trust.TrustedDevice, want ...string) {
	t.Helper()
	sort.Strings(want)
	ids := trustedIDs(got)
	if len(ids) != len(want) {
		t.Fatalf("trusted = %v, want %v", ids, want)
	}
	for i := range ids {
		if ids[i] != want[i] {
			t.Fatalf("trusted = %v, want %v", ids, want)
		}
	}
}

func TestAnchorAloneIsTrusted(t *testing.T) {
	root := newDev("root")
	got := trust.ComputeTrusted(nil, []trust.Anchor{root.anchor()})
	assertTrusted(t, got, "root")
	if got["root"].EncPub != root.enc {
		t.Fatalf("anchor enc key not carried: %+v", got["root"])
	}
}

func TestVouchChainAdmits(t *testing.T) {
	root, a, b := newDev("root"), newDev("a"), newDev("b")
	certs := []trust.Cert{vouchFor(t, root, a), vouchFor(t, a, b)}
	got := trust.ComputeTrusted(certs, []trust.Anchor{root.anchor()})
	assertTrusted(t, got, "root", "a", "b")
	// Keys of vouched devices come from the vouch itself.
	if got["b"].SignPub != b.sign.Public || got["b"].EncPub != b.enc {
		t.Fatalf("vouched keys not carried: %+v", got["b"])
	}
}

func TestUntrustedIssuerVouchIgnored(t *testing.T) {
	// stranger is not reachable from the anchor, so its vouch admits no one.
	root, stranger, victim := newDev("root"), newDev("stranger"), newDev("victim")
	certs := []trust.Cert{vouchFor(t, stranger, victim)}
	got := trust.ComputeTrusted(certs, []trust.Anchor{root.anchor()})
	assertTrusted(t, got, "root")
}

func TestTamperedVouchIgnored(t *testing.T) {
	root, a := newDev("root"), newDev("a")
	c := vouchFor(t, root, a)
	c.SubjectEncPub = "age1-attacker" // swap the recipient key the vouch attests
	got := trust.ComputeTrusted([]trust.Cert{c}, []trust.Anchor{root.anchor()})
	assertTrusted(t, got, "root")
}

func TestRevokeCascadesToSubtree(t *testing.T) {
	// root -> a -> {b, c}; revoke a (root is a's ancestor) cuts a, b, and c.
	root, a, b, c := newDev("root"), newDev("a"), newDev("b"), newDev("c")
	certs := []trust.Cert{
		vouchFor(t, root, a),
		vouchFor(t, a, b),
		vouchFor(t, a, c),
		revokeOf(t, root, a),
	}
	got := trust.ComputeTrusted(certs, []trust.Anchor{root.anchor()})
	assertTrusted(t, got, "root")
}

func TestSelfRevoke(t *testing.T) {
	root, a := newDev("root"), newDev("a")
	certs := []trust.Cert{vouchFor(t, root, a), revokeOf(t, a, a)}
	got := trust.ComputeTrusted(certs, []trust.Anchor{root.anchor()})
	assertTrusted(t, got, "root")
}

func TestRevokeByNonAncestorIgnored(t *testing.T) {
	// Siblings a and b under root. b cannot revoke a (not its ancestor).
	root, a, b := newDev("root"), newDev("a"), newDev("b")
	certs := []trust.Cert{
		vouchFor(t, root, a),
		vouchFor(t, root, b),
		revokeOf(t, b, a),
	}
	got := trust.ComputeTrusted(certs, []trust.Anchor{root.anchor()})
	assertTrusted(t, got, "root", "a", "b")
}

func TestMultiplePathsSurviveRevoke(t *testing.T) {
	// b is vouched by both a and root. Revoking a leaves b trusted via root.
	root, a, b := newDev("root"), newDev("a"), newDev("b")
	certs := []trust.Cert{
		vouchFor(t, root, a),
		vouchFor(t, a, b),
		vouchFor(t, root, b),
		revokeOf(t, root, a),
	}
	got := trust.ComputeTrusted(certs, []trust.Anchor{root.anchor()})
	assertTrusted(t, got, "root", "b")
}

func TestMultipleAnchors(t *testing.T) {
	// Two independently-verified anchors; each vouches a distinct device.
	r1, r2, a, b := newDev("r1"), newDev("r2"), newDev("a"), newDev("b")
	certs := []trust.Cert{vouchFor(t, r1, a), vouchFor(t, r2, b)}
	got := trust.ComputeTrusted(certs, []trust.Anchor{r1.anchor(), r2.anchor()})
	assertTrusted(t, got, "r1", "r2", "a", "b")
}
