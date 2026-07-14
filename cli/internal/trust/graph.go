package trust

import (
	"fmt"
	"sort"
)

// Anchor is a device signing identity this device verified out-of-band — its own
// at link, or an inviter's roster entries via the invite code — and roots trust
// at. Reachability in the vouch graph starts from anchors; nothing is trusted
// that does not chain back to one.
type Anchor struct {
	DeviceID string
	EncPub   string // age public key, so anchors are themselves valid recipients
	SignPub  string // Ed25519, verifies the anchor's certs
}

// AnchorRepository persists this device's trust anchors. It is the port; the
// SQLite implementation is the adapter in internal/vault.
type AnchorRepository interface {
	Save(a Anchor) error // upsert by device id
	List() ([]Anchor, error)
}

// TrustedDevice is a device admitted to the trusted set, carrying the keys needed
// to seal to it (EncPub) and to verify its certs (SignPub).
type TrustedDevice struct {
	DeviceID string
	EncPub   string
	SignPub  string
}

// ComputeTrusted derives the trusted device set from the full signed cert log and
// this device's anchors. A device is trusted iff it is reachable from an anchor
// through valid, non-revoked vouches, where each vouch must be signed by an
// already-trusted issuer. Revoking a device removes it and everything reachable
// only through it (cascade); a revoke counts only if its issuer is the target
// itself (self-revoke) or an ancestor of the target in the vouch graph.
//
// The function is pure and deterministic. It defends against a hostile relay on
// three fronts:
//   - Each issuer's certs must form an intact hash chain (validChains); a dropped,
//     reordered, or tampered cert breaks the chain and its whole tail falls away,
//     so the relay cannot silently rewrite a device's history.
//   - Signatures are verified here with keys discovered during admission, so a
//     forged cert never admits anyone.
//   - A device's keys are bound by the vouch that first admits it; a later vouch
//     that contradicts that binding is ignored, not allowed to rebind the identity.
//
// Residual: the *first* admitting vouch for a fresh id still sets its keys, so a
// trusted device that learns a not-yet-joined id could race the legitimate inviter
// to bind it. Closing that fully needs enrollment-attested identity (the server
// vouching for the keys a device joined with); see docs/sync_design.md §11.
func ComputeTrusted(certs []Cert, anchors []Anchor) map[string]TrustedDevice {
	a := admit(validChains(certs), anchors)

	// Phase 2 — collect valid revocations. A revoke counts only if its issuer is
	// admitted, it verifies, and the issuer is the target (self-revoke) or an
	// ancestor of the target in the *admission* graph — i.e. it actually introduced
	// the target, directly or transitively.
	revoked := map[string]bool{}
	for _, c := range a.certs {
		if c.Kind != KindRevoke {
			continue
		}
		issuerKey, ok := a.signPub[c.IssuerID]
		if !ok || !a.admitted[c.IssuerID] || c.Verify(issuerKey) != nil {
			continue
		}
		if c.IssuerID == c.TargetID || isAncestor(a.authEdges, c.IssuerID, c.TargetID) {
			revoked[c.TargetID] = true
		}
	}

	// Phase 3 — effective trust is reachability from the (non-revoked) anchors
	// over reach edges, never entering a revoked device. This is what drops the
	// subtree of a revoked voucher while letting a redundantly-vouched device
	// survive through its other path.
	trusted := map[string]TrustedDevice{}
	var stack []string
	for _, an := range anchors {
		if revoked[an.DeviceID] {
			continue
		}
		stack = append(stack, an.DeviceID)
	}
	for len(stack) > 0 {
		id := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		if _, done := trusted[id]; done {
			continue
		}
		trusted[id] = TrustedDevice{DeviceID: id, EncPub: a.encPub[id], SignPub: a.signPub[id]}
		for _, sub := range a.reachEdges[id] {
			if !revoked[sub] {
				stack = append(stack, sub)
			}
		}
	}
	return trusted
}

// admission is the result of the fixpoint admission pass: the keys discovered for
// every reachable device (including ones later revoked) and the two edge sets.
type admission struct {
	certs                 []Cert            // the validated certs it ran over
	signPub, encPub       map[string]string // device id -> signing / age key
	reachEdges, authEdges map[string][]string
	admitted              map[string]bool
}

// admit runs Phase 1 — admission to a fixpoint — over already chain-validated
// certs. A vouch admits its subject once its issuer's key is known (issuer already
// admitted) and it verifies under that key. Two edge sets are kept, because
// reachability and revoke-authority are different questions:
//   - reachEdges records *every* valid vouch by a trusted issuer. It answers "is
//     this device still connected to an anchor?", so redundant vouches add
//     resilience — a device with two vouchers survives losing one.
//   - authEdges records only the *admitting* vouch (the one that first brought the
//     subject in). It answers "who may revoke this device?". A gratuitous re-vouch
//     of an already-trusted device records no auth edge, so a member cannot
//     fabricate ancestry over a device — or the root — it did not introduce.
func admit(certs []Cert, anchors []Anchor) admission {
	signPub := map[string]string{}
	encPub := map[string]string{}
	for _, a := range anchors {
		signPub[a.DeviceID] = a.SignPub
		encPub[a.DeviceID] = a.EncPub
	}
	reachEdges := map[string][]string{}
	authEdges := map[string][]string{}
	admitted := map[string]bool{}
	for id := range signPub {
		admitted[id] = true
	}
	for {
		changed := false
		for _, c := range certs {
			if c.Kind != KindVouch {
				continue
			}
			issuerKey, ok := signPub[c.IssuerID]
			if !ok || c.Verify(issuerKey) != nil {
				continue // issuer not (yet) trusted, or the cert does not verify
			}
			// Identity binding: a vouch may not contradict keys already held for the
			// subject (from an anchor or a prior admitting vouch). Such a cert is a
			// rebind attempt and is ignored entirely (no edge of either kind).
			if sp, known := signPub[c.SubjectID]; known &&
				(sp != c.SubjectSignPub || encPub[c.SubjectID] != c.SubjectEncPub) {
				continue
			}
			reachEdges[c.IssuerID] = appendUnique(reachEdges[c.IssuerID], c.SubjectID)
			if admitted[c.SubjectID] {
				continue // already in; a re-vouch grants reachability, never authority
			}
			admitted[c.SubjectID] = true
			signPub[c.SubjectID] = c.SubjectSignPub
			encPub[c.SubjectID] = c.SubjectEncPub
			authEdges[c.IssuerID] = appendUnique(authEdges[c.IssuerID], c.SubjectID)
			changed = true
		}
		if !changed {
			break
		}
	}
	return admission{
		certs: certs, signPub: signPub, encPub: encPub,
		reachEdges: reachEdges, authEdges: authEdges, admitted: admitted,
	}
}

// Head is the verified tip of one issuer's cert chain: the highest contiguous seq
// whose signature (and the whole prefix below it) verifies under the issuer's key.
type Head struct {
	Seq  int64
	Hash string
}

// TrustHeadRepository persists the highest verified head seen per issuer, so a
// later pull can detect a relay that rolled back or withheld a chain's tail. It is
// the port; the SQLite implementation is the adapter in internal/vault.
type TrustHeadRepository interface {
	List() (map[string]Head, error)     // issuer id -> last accepted head
	Save(issuerID string, h Head) error // upsert by issuer id
}

// CheckProgress verifies that the current verified chains do not regress below the
// heads previously accepted (in seen): an issuer whose head seq dropped, or that
// vanished from the log entirely, means a relay rolled back or withheld its tail —
// e.g. suppressing a revoke — and is rejected. On success it returns the advanced
// heads to persist. It does not catch a relay that withholds a cert it never
// revealed in the first place (no baseline exists for it); that needs a signed log
// head from the server (deferred, see docs/sync_design.md §11).
func CheckProgress(chains map[string][]Cert, seen map[string]Head) (map[string]Head, error) {
	for issuer, prev := range seen {
		chain, ok := chains[issuer]
		if !ok {
			return nil, fmt.Errorf(
				"trust: issuer %s chain (seen through seq %d) is gone from the log — relay rollback",
				issuer, prev.Seq)
		}
		if tip := Tip(chain); tip.Seq < prev.Seq {
			return nil, fmt.Errorf(
				"trust: issuer %s chain rolled back from seq %d to %d — relay rollback",
				issuer, prev.Seq, tip.Seq)
		}
	}
	heads := make(map[string]Head, len(chains))
	for issuer, chain := range chains {
		heads[issuer] = Tip(chain)
	}
	return heads, nil
}

// VerifiedChains returns, per issuer whose signing key is known, that issuer's
// signature-verified contiguous cert chain (seq 0..N, stopping at the first gap or
// bad signature). Because only the issuer can produce a valid signature, a relay
// cannot extend a chain past the issuer's real certs — so the tip of each returned
// chain is the issuer's true head, injection-proof. Revoked issuers are included:
// their history is still real and must not appear to vanish. This is the basis for
// (a) a device signing its own next cert onto its real head, and (b) detecting a
// relay that rolls back or withholds an issuer's tail.
func VerifiedChains(certs []Cert, anchors []Anchor) map[string][]Cert {
	byIssuer := validChainsByIssuer(certs)
	a := admit(flatten(byIssuer), anchors)
	out := map[string][]Cert{}
	for issuer, key := range a.signPub {
		var verified []Cert
		for _, c := range byIssuer[issuer] {
			if c.Verify(key) != nil {
				break
			}
			verified = append(verified, c)
		}
		if len(verified) > 0 {
			out[issuer] = verified
		}
	}
	return out
}

// Tip returns the head (seq + hash) of a verified chain, or a zero Head with
// Seq -1 for an empty chain (no certs published yet).
func Tip(chain []Cert) Head {
	if len(chain) == 0 {
		return Head{Seq: -1}
	}
	last := chain[len(chain)-1]
	return Head{Seq: last.Seq, Hash: last.Hash()}
}

// flatten concatenates per-issuer chains in a deterministic issuer order.
func flatten(byIssuer map[string][]Cert) []Cert {
	issuers := make([]string, 0, len(byIssuer))
	for id := range byIssuer {
		issuers = append(issuers, id)
	}
	sort.Strings(issuers)
	var out []Cert
	for _, id := range issuers {
		out = append(out, byIssuer[id]...)
	}
	return out
}

// validChainsByIssuer keeps, for each issuer, only the longest prefix of its certs
// that forms an intact hash chain: seq starts at 0 and increments by one, and each
// cert's PrevHash equals the previous cert's Hash. A gap, a reordering, or a
// tampered or withheld cert breaks the chain, and everything past the break is
// dropped — so a relay that reorders or truncates a device's history cannot make
// the survivors look contiguous. Signatures are checked later, during admission.
//
// The result is deterministic even under a hostile log: certs are ordered by seq
// with a hash tiebreak, so two certs a relay forged at the same seq resolve the
// same way on every device (and the chain simply breaks at the duplicate).
func validChainsByIssuer(certs []Cert) map[string][]Cert {
	grouped := map[string][]Cert{}
	for _, c := range certs {
		grouped[c.IssuerID] = append(grouped[c.IssuerID], c)
	}
	out := make(map[string][]Cert, len(grouped))
	for id, group := range grouped {
		sort.SliceStable(group, func(i, j int) bool {
			if group[i].Seq != group[j].Seq {
				return group[i].Seq < group[j].Seq
			}
			return group[i].Hash() < group[j].Hash() // total order on hostile duplicates
		})
		var chain []Cert
		var expectedSeq int64
		prevHash := ""
		for _, c := range group {
			if c.Seq != expectedSeq || c.PrevHash != prevHash {
				break
			}
			chain = append(chain, c)
			prevHash = c.Hash()
			expectedSeq++
		}
		if len(chain) > 0 {
			out[id] = chain
		}
	}
	return out
}

// validChains flattens validChainsByIssuer into one slice, in a deterministic
// issuer order.
func validChains(certs []Cert) []Cert {
	return flatten(validChainsByIssuer(certs))
}

// isAncestor reports whether from can reach to over vouch edges (from vouched to,
// directly or transitively). Guards against cycles.
func isAncestor(edges map[string][]string, from, to string) bool {
	seen := map[string]bool{from: true}
	stack := append([]string(nil), edges[from]...)
	for len(stack) > 0 {
		n := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		if n == to {
			return true
		}
		if seen[n] {
			continue
		}
		seen[n] = true
		stack = append(stack, edges[n]...)
	}
	return false
}

func appendUnique(xs []string, x string) []string {
	for _, e := range xs {
		if e == x {
			return xs
		}
	}
	return append(xs, x)
}
