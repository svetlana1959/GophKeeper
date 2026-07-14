package trust

import "sort"

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
	certs = validChains(certs)

	signPub := map[string]string{} // device id -> signing key, as we learn it
	encPub := map[string]string{}  // device id -> age key
	for _, a := range anchors {
		signPub[a.DeviceID] = a.SignPub
		encPub[a.DeviceID] = a.EncPub
	}

	// Phase 1 — admission to a fixpoint. A vouch admits its subject once its
	// issuer's key is known (issuer already admitted) and it verifies under that
	// key. Two edge sets are kept, because reachability and revoke-authority are
	// different questions:
	//   - reachEdges records *every* valid vouch by a trusted issuer. It answers
	//     "is this device still connected to an anchor?" (Phase 3), so redundant
	//     vouches add resilience — a device with two vouchers survives losing one.
	//   - authEdges records only the *admitting* vouch (the one that first brought
	//     the subject in). It answers "who may revoke this device?" (Phase 2). A
	//     gratuitous re-vouch of an already-trusted device records no auth edge, so
	//     a member cannot fabricate ancestry over a device — or the root — it did
	//     not actually introduce.
	reachEdges := map[string][]string{} // issuer -> every subject it validly vouched
	authEdges := map[string][]string{}  // issuer -> subjects it admitted (introduced)
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

	// Phase 2 — collect valid revocations. A revoke counts only if its issuer is
	// admitted, it verifies, and the issuer is the target (self-revoke) or an
	// ancestor of the target in the *admission* graph — i.e. it actually introduced
	// the target, directly or transitively.
	revoked := map[string]bool{}
	for _, c := range certs {
		if c.Kind != KindRevoke {
			continue
		}
		issuerKey, ok := signPub[c.IssuerID]
		if !ok || !admitted[c.IssuerID] || c.Verify(issuerKey) != nil {
			continue
		}
		if c.IssuerID == c.TargetID || isAncestor(authEdges, c.IssuerID, c.TargetID) {
			revoked[c.TargetID] = true
		}
	}

	// Phase 3 — effective trust is reachability from the (non-revoked) anchors
	// over reach edges, never entering a revoked device. This is what drops the
	// subtree of a revoked voucher while letting a redundantly-vouched device
	// survive through its other path.
	trusted := map[string]TrustedDevice{}
	var stack []string
	for _, a := range anchors {
		if revoked[a.DeviceID] {
			continue
		}
		stack = append(stack, a.DeviceID)
	}
	for len(stack) > 0 {
		id := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		if _, done := trusted[id]; done {
			continue
		}
		trusted[id] = TrustedDevice{DeviceID: id, EncPub: encPub[id], SignPub: signPub[id]}
		for _, sub := range reachEdges[id] {
			if !revoked[sub] {
				stack = append(stack, sub)
			}
		}
	}
	return trusted
}

// validChains keeps, for each issuer, only the longest prefix of its certs that
// forms an intact hash chain: seq starts at 0 and increments by one, and each
// cert's PrevHash equals the previous cert's Hash. A gap, a reordering, or a
// tampered or withheld cert breaks the chain, and everything past the break is
// dropped — so a relay that reorders or truncates a device's history cannot make
// the survivors look contiguous. Signatures are checked later, during admission.
func validChains(certs []Cert) []Cert {
	byIssuer := map[string][]Cert{}
	for _, c := range certs {
		byIssuer[c.IssuerID] = append(byIssuer[c.IssuerID], c)
	}
	// Iterate issuers in a stable order so the result is deterministic.
	issuers := make([]string, 0, len(byIssuer))
	for id := range byIssuer {
		issuers = append(issuers, id)
	}
	sort.Strings(issuers)

	var out []Cert
	for _, id := range issuers {
		group := byIssuer[id]
		sort.Slice(group, func(i, j int) bool { return group[i].Seq < group[j].Seq })
		var expectedSeq int64
		prevHash := ""
		for _, c := range group {
			if c.Seq != expectedSeq || c.PrevHash != prevHash {
				break
			}
			out = append(out, c)
			prevHash = c.Hash()
			expectedSeq++
		}
	}
	return out
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
