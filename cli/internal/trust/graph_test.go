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

// log builds a signed cert log, assigning each issuer a contiguous, hash-linked
// seq automatically — the shape ComputeTrusted's chain check (validChains) now
// requires. Use it whenever an issuer emits more than one cert.
type log struct {
	t     *testing.T
	next  map[string]int64
	prev  map[string]string
	certs []trust.Cert
}

func newLog(t *testing.T) *log {
	return &log{t: t, next: map[string]int64{}, prev: map[string]string{}}
}

func (l *log) push(issuer dev, c trust.Cert) trust.Cert {
	l.t.Helper()
	c.Seq = l.next[issuer.id]
	c.PrevHash = l.prev[issuer.id]
	signed, err := trust.Sign(c, issuer.sign.Private)
	if err != nil {
		l.t.Fatalf("sign cert: %v", err)
	}
	l.next[issuer.id] = signed.Seq + 1
	l.prev[issuer.id] = signed.Hash()
	l.certs = append(l.certs, signed)
	return signed
}

func (l *log) vouch(issuer, subject dev) trust.Cert {
	return l.push(issuer, trust.Cert{
		Kind: trust.KindVouch, AccountID: "acct", IssuerID: issuer.id,
		SubjectID: subject.id, SubjectEncPub: subject.enc, SubjectSignPub: subject.sign.Public,
	})
}

func (l *log) revoke(issuer, target dev) trust.Cert {
	return l.push(issuer, trust.Cert{
		Kind: trust.KindRevoke, AccountID: "acct", IssuerID: issuer.id, TargetID: target.id,
	})
}

// vouchFor / revokeOf sign a single cert at seq 0 — fine when an issuer emits at
// most one cert; use newLog otherwise so the per-issuer chain stays contiguous.
func vouchFor(t *testing.T, issuer, subject dev) trust.Cert {
	t.Helper()
	return newLog(t).vouch(issuer, subject)
}

func revokeOf(t *testing.T, issuer, target dev) trust.Cert {
	t.Helper()
	return newLog(t).revoke(issuer, target)
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
	l := newLog(t)
	l.vouch(root, a)
	l.vouch(a, b)
	l.vouch(a, c)
	l.revoke(root, a)
	got := trust.ComputeTrusted(l.certs, []trust.Anchor{root.anchor()})
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
	l := newLog(t)
	l.vouch(root, a)
	l.vouch(root, b)
	l.revoke(b, a)
	got := trust.ComputeTrusted(l.certs, []trust.Anchor{root.anchor()})
	assertTrusted(t, got, "root", "a", "b")
}

// TestRevokeAfterPrimingVouchIgnored is the regression for the authority-bypass:
// a trusted sibling b vouches an already-trusted device a (a "priming" vouch) to
// try to become its ancestor, then revokes it. The priming vouch must grant no
// revoke authority, so a survives. Pointed at the root, the same trick would
// collapse the whole account.
func TestRevokeAfterPrimingVouchIgnored(t *testing.T) {
	root, a, b := newDev("root"), newDev("a"), newDev("b")
	l := newLog(t)
	l.vouch(root, a) // a admitted by root
	l.vouch(root, b) // b admitted by root
	l.vouch(b, a)    // priming: b re-vouches already-trusted a
	l.revoke(b, a)   // b tries to cut a
	got := trust.ComputeTrusted(l.certs, []trust.Anchor{root.anchor()})
	assertTrusted(t, got, "root", "a", "b")

	// The same attack aimed at the root must not collapse the account either.
	l2 := newLog(t)
	l2.vouch(root, a)
	l2.vouch(root, b)
	l2.vouch(b, root)
	l2.revoke(b, root)
	got2 := trust.ComputeTrusted(l2.certs, []trust.Anchor{root.anchor()})
	assertTrusted(t, got2, "root", "a", "b")
}

// TestChainGapDropsTail is the regression for chain verification: a relay that
// drops an issuer's seq-1 cert cannot make seq 2 apply, because seq 2's PrevHash
// no longer matches. Here root's revoke of a (seq 2) is orphaned once its vouch of
// b (seq 1) is withheld, so a stays trusted.
func TestChainGapDropsTail(t *testing.T) {
	root, a, b := newDev("root"), newDev("a"), newDev("b")
	l := newLog(t)
	l.vouch(root, a)             // seq 0
	withheld := l.vouch(root, b) // seq 1 — dropped by the relay below
	l.revoke(root, a)            // seq 2 — chains off seq 1

	var delivered []trust.Cert
	for _, c := range l.certs {
		if c.Seq == withheld.Seq && c.IssuerID == withheld.IssuerID {
			continue // relay withholds seq 1
		}
		delivered = append(delivered, c)
	}
	got := trust.ComputeTrusted(delivered, []trust.Anchor{root.anchor()})
	assertTrusted(t, got, "root", "a") // revoke (seq 2) never applies; b absent
}

// TestRebindVouchIgnored is the regression for identity binding: once a device's
// keys are established, a later vouch that reuses its id with different keys is
// ignored, so a trusted member cannot rebind a victim id's recipient key.
func TestRebindVouchIgnored(t *testing.T) {
	root, a, b := newDev("root"), newDev("a"), newDev("b")
	l := newLog(t)
	l.vouch(root, a) // a bound to a's real keys
	l.vouch(root, b)
	// b vouches a's id but swaps in an attacker recipient key.
	rebind := trust.Cert{
		Kind: trust.KindVouch, AccountID: "acct", IssuerID: b.id,
		SubjectID: a.id, SubjectEncPub: "age1-attacker", SubjectSignPub: a.sign.Public,
	}
	l.push(b, rebind)
	got := trust.ComputeTrusted(l.certs, []trust.Anchor{root.anchor()})
	assertTrusted(t, got, "root", "a", "b")
	if got["a"].EncPub != a.enc {
		t.Fatalf("identity rebound: a.EncPub = %q, want %q", got["a"].EncPub, a.enc)
	}
}

func TestMultiplePathsSurviveRevoke(t *testing.T) {
	// b is vouched by both a and root. Revoking a leaves b trusted via root.
	root, a, b := newDev("root"), newDev("a"), newDev("b")
	l := newLog(t)
	l.vouch(root, a)
	l.vouch(a, b)
	l.vouch(root, b)
	l.revoke(root, a)
	got := trust.ComputeTrusted(l.certs, []trust.Anchor{root.anchor()})
	assertTrusted(t, got, "root", "b")
}

func TestMultipleAnchors(t *testing.T) {
	// Two independently-verified anchors; each vouches a distinct device.
	r1, r2, a, b := newDev("r1"), newDev("r2"), newDev("a"), newDev("b")
	certs := []trust.Cert{vouchFor(t, r1, a), vouchFor(t, r2, b)}
	got := trust.ComputeTrusted(certs, []trust.Anchor{r1.anchor(), r2.anchor()})
	assertTrusted(t, got, "r1", "r2", "a", "b")
}

// TestVerifiedChainsStopsAtForgedTip: a relay appends a cert under an issuer's id
// at the next contiguous seq with a correct prev_hash but a signature it cannot
// forge. VerifiedChains must return only the issuer's genuinely-signed prefix, so
// the tip used for the device's own next publish is its real head.
func TestVerifiedChainsStopsAtForgedTip(t *testing.T) {
	root, a := newDev("root"), newDev("a")
	l := newLog(t)
	l.vouch(root, a) // root seq 0, genuinely signed

	// Relay forges root's seq 1, chaining onto seq 0's real hash but signing with
	// an attacker key (it lacks root's signing key).
	attacker, _ := crypto.GenerateSigningKey()
	forged := trust.Cert{
		Kind: trust.KindVouch, AccountID: "acct", IssuerID: root.id,
		Seq: 1, PrevHash: l.certs[0].Hash(),
		SubjectID: "ghost", SubjectEncPub: "age1-ghost", SubjectSignPub: attacker.Public,
	}
	forged, _ = trust.Sign(forged, attacker.Private)

	chains := trust.VerifiedChains(append(l.certs, forged), []trust.Anchor{root.anchor()})
	if got := trust.Tip(chains[root.id]); got.Seq != 0 {
		t.Fatalf("verified tip = seq %d, want 0 (forged seq 1 must not count)", got.Seq)
	}
}

// TestVerifiedChainsIncludesRevokedIssuer: a revoked device's own chain history is
// still real and must remain visible (else a later pull would look like the relay
// made it vanish).
func TestVerifiedChainsIncludesRevokedIssuer(t *testing.T) {
	root, a, b := newDev("root"), newDev("a"), newDev("b")
	l := newLog(t)
	l.vouch(root, a)
	l.vouch(a, b) // a vouches b (a is an issuer)
	l.revoke(root, a)
	chains := trust.VerifiedChains(l.certs, []trust.Anchor{root.anchor()})
	if _, ok := chains["a"]; !ok {
		t.Fatalf("revoked issuer a dropped from verified chains: %v", chains)
	}
}

// TestCheckProgressRejectsRollback: once we have seen an issuer's chain to seq N,
// a later log that presents fewer of its certs (a relay suppressing the tail, e.g.
// a revoke) is refused; a genuinely advancing log is accepted.
func TestCheckProgressRejectsRollback(t *testing.T) {
	root, a := newDev("root"), newDev("a")
	l := newLog(t)
	l.vouch(root, a)  // root seq 0
	l.revoke(root, a) // root seq 1 (the tail a hostile relay would hide)
	anchors := []trust.Anchor{root.anchor()}

	full := trust.VerifiedChains(l.certs, anchors)
	seen, err := trust.CheckProgress(full, map[string]trust.Head{})
	if err != nil {
		t.Fatalf("first CheckProgress: %v", err)
	}
	if seen[root.id].Seq != 1 {
		t.Fatalf("seen head = %d, want 1", seen[root.id].Seq)
	}

	// Relay now serves only root's seq 0 (revoke withheld).
	truncated := trust.VerifiedChains(l.certs[:1], anchors)
	if _, err := trust.CheckProgress(truncated, seen); err == nil {
		t.Fatalf("rollback from seq 1 to 0 was accepted, want refusal")
	}

	// A log that still has the full chain is fine.
	if _, err := trust.CheckProgress(full, seen); err != nil {
		t.Fatalf("non-regressing log refused: %v", err)
	}
}

// TestValidChainsDeterministicOnDuplicateSeq: a relay serving two different certs
// at the same seq must yield the same result on every device (deterministic), and
// the chain breaks at the ambiguity rather than picking arbitrarily each run.
func TestValidChainsDeterministicOnDuplicateSeq(t *testing.T) {
	root, a, b := newDev("root"), newDev("a"), newDev("b")
	c0 := vouchFor(t, root, a) // root seq 0
	// Two distinct seq-0 certs from root (only a hostile relay produces this).
	dupA := c0
	dupB := trust.Cert{
		Kind: trust.KindVouch, AccountID: "acct", IssuerID: root.id,
		SubjectID: b.id, SubjectEncPub: b.enc, SubjectSignPub: b.sign.Public,
	}
	dupB, _ = trust.Sign(dupB, root.sign.Private)

	anchors := []trust.Anchor{root.anchor()}
	first := trust.ComputeTrusted([]trust.Cert{dupA, dupB}, anchors)
	for i := 0; i < 20; i++ {
		got := trust.ComputeTrusted([]trust.Cert{dupB, dupA}, anchors) // reversed input
		if len(got) != len(first) {
			t.Fatalf("non-deterministic under duplicate seq: %v vs %v", trustedIDs(got), trustedIDs(first))
		}
		for id := range first {
			if _, ok := got[id]; !ok {
				t.Fatalf("non-deterministic under duplicate seq: %v vs %v", trustedIDs(got), trustedIDs(first))
			}
		}
	}
}
