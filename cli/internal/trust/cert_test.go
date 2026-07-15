package trust_test

import (
	"errors"
	"testing"

	"github.com/svetlana1959/GophKeeper/cli/internal/crypto"
	"github.com/svetlana1959/GophKeeper/cli/internal/trust"
)

func vouch(issuer, subject string) trust.Cert {
	return trust.Cert{
		Kind:           trust.KindVouch,
		AccountID:      "acct-1",
		IssuerID:       issuer,
		Seq:            0,
		SubjectID:      subject,
		SubjectEncPub:  "age1-" + subject,
		SubjectSignPub: "sign-" + subject,
		IssuedAt:       1_700_000_000,
	}
}

func TestVouchSignVerify(t *testing.T) {
	kp, _ := crypto.GenerateSigningKey()
	c, err := trust.Sign(vouch("dev-a", "dev-b"), kp.Private)
	if err != nil {
		t.Fatalf("Sign: %v", err)
	}
	if c.Sig == "" {
		t.Fatal("Sig not set")
	}
	if err := c.Verify(kp.Public); err != nil {
		t.Fatalf("Verify: %v", err)
	}
}

func TestRevokeSignVerify(t *testing.T) {
	kp, _ := crypto.GenerateSigningKey()
	rc := trust.Cert{
		Kind:      trust.KindRevoke,
		AccountID: "acct-1",
		IssuerID:  "dev-a",
		Seq:       3,
		PrevHash:  "abc",
		TargetID:  "dev-b",
		IssuedAt:  1_700_000_100,
	}
	signed, err := trust.Sign(rc, kp.Private)
	if err != nil {
		t.Fatalf("Sign: %v", err)
	}
	if err := signed.Verify(kp.Public); err != nil {
		t.Fatalf("Verify: %v", err)
	}
}

func TestVerifyRejectsTamperedField(t *testing.T) {
	kp, _ := crypto.GenerateSigningKey()
	c, _ := trust.Sign(vouch("dev-a", "dev-b"), kp.Private)

	c.SubjectEncPub = "age1-attacker" // swap the recipient key the cert attests
	if err := c.Verify(kp.Public); !errors.Is(err, crypto.ErrBadSignature) {
		t.Fatalf("Verify tampered = %v, want ErrBadSignature", err)
	}
}

func TestVerifyRejectsWrongIssuerKey(t *testing.T) {
	signer, _ := crypto.GenerateSigningKey()
	other, _ := crypto.GenerateSigningKey()
	c, _ := trust.Sign(vouch("dev-a", "dev-b"), signer.Private)

	if err := c.Verify(other.Public); !errors.Is(err, crypto.ErrBadSignature) {
		t.Fatalf("Verify wrong issuer = %v, want ErrBadSignature", err)
	}
}

func TestVouchAndRevokeDoNotCollide(t *testing.T) {
	// A revoke must not verify under a vouch's signature even with matching
	// scalar fields — domain separation in canonical() prevents cross-kind reuse.
	kp, _ := crypto.GenerateSigningKey()
	v, _ := trust.Sign(vouch("dev-a", "dev-b"), kp.Private)

	forged := trust.Cert{
		Kind: trust.KindRevoke, AccountID: v.AccountID, IssuerID: v.IssuerID,
		Seq: v.Seq, PrevHash: v.PrevHash, TargetID: v.SubjectID, IssuedAt: v.IssuedAt,
		Sig: v.Sig,
	}
	if err := forged.Verify(kp.Public); !errors.Is(err, crypto.ErrBadSignature) {
		t.Fatalf("cross-kind verify = %v, want ErrBadSignature", err)
	}
}

func TestUnknownKind(t *testing.T) {
	_, err := trust.Sign(trust.Cert{Kind: "bogus"}, "x")
	if !errors.Is(err, trust.ErrUnknownKind) {
		t.Fatalf("Sign unknown kind = %v, want ErrUnknownKind", err)
	}
}

func TestHashChainsOnSignature(t *testing.T) {
	kp, _ := crypto.GenerateSigningKey()
	c, _ := trust.Sign(vouch("dev-a", "dev-b"), kp.Private)

	if c.Hash() == "" {
		t.Fatal("signed cert hashed to empty")
	}
	// An unsigned cert has no chain hash.
	unsigned := vouch("dev-a", "dev-b")
	if unsigned.Hash() != "" {
		t.Fatalf("unsigned Hash = %q, want empty", unsigned.Hash())
	}
	// Two distinct signed certs hash differently.
	c2, _ := trust.Sign(vouch("dev-a", "dev-c"), kp.Private)
	if c.Hash() == c2.Hash() {
		t.Fatal("distinct certs share a hash")
	}
}
