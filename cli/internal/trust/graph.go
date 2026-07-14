package trust

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
// The function is pure and deterministic: signatures are verified here using keys
// discovered during admission, so a forged or tampered cert simply never admits
// anyone.
func ComputeTrusted(certs []Cert, anchors []Anchor) map[string]TrustedDevice {
	signPub := map[string]string{} // device id -> signing key, as we learn it
	encPub := map[string]string{}  // device id -> age key
	for _, a := range anchors {
		signPub[a.DeviceID] = a.SignPub
		encPub[a.DeviceID] = a.EncPub
	}

	// Phase 1 — admission to a fixpoint. A vouch admits its subject once its
	// issuer's key is known (issuer already admitted) and it verifies under that
	// key. Edges records who vouched whom, for later reachability/ancestry.
	edges := map[string][]string{} // issuer -> subjects it validly vouched
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
			edges[c.IssuerID] = appendUnique(edges[c.IssuerID], c.SubjectID)
			if admitted[c.SubjectID] {
				continue
			}
			admitted[c.SubjectID] = true
			if _, seen := signPub[c.SubjectID]; !seen {
				signPub[c.SubjectID] = c.SubjectSignPub
				encPub[c.SubjectID] = c.SubjectEncPub
			}
			changed = true
		}
		if !changed {
			break
		}
	}

	// Phase 2 — collect valid revocations. A revoke counts only if its issuer is
	// admitted, it verifies, and the issuer is the target (self-revoke) or an
	// ancestor of the target in the vouch graph.
	revoked := map[string]bool{}
	for _, c := range certs {
		if c.Kind != KindRevoke {
			continue
		}
		issuerKey, ok := signPub[c.IssuerID]
		if !ok || !admitted[c.IssuerID] || c.Verify(issuerKey) != nil {
			continue
		}
		if c.IssuerID == c.TargetID || isAncestor(edges, c.IssuerID, c.TargetID) {
			revoked[c.TargetID] = true
		}
	}

	// Phase 3 — effective trust is reachability from the (non-revoked) anchors
	// over vouch edges, never entering a revoked device. This is what drops the
	// subtree of a revoked voucher.
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
		for _, sub := range edges[id] {
			if !revoked[sub] {
				stack = append(stack, sub)
			}
		}
	}
	return trusted
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
