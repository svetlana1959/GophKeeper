package vault_test

import (
	"testing"

	"github.com/svetlana1959/GophKeeper/cli/internal/trust"
)

func TestTrustHeads_SaveListAndUpsert(t *testing.T) {
	db, _ := openTestDB(t)
	heads := db.TrustHeads()

	// Empty to start.
	got, err := heads.List()
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(got) != 0 {
		t.Fatalf("fresh vault has %d heads, want 0", len(got))
	}

	if err := heads.Save("issuer-a", trust.Head{Seq: 1, Hash: "hash-1"}); err != nil {
		t.Fatalf("Save a: %v", err)
	}
	if err := heads.Save("issuer-b", trust.Head{Seq: 5, Hash: "hash-b"}); err != nil {
		t.Fatalf("Save b: %v", err)
	}
	// Upsert: same issuer advances in place.
	if err := heads.Save("issuer-a", trust.Head{Seq: 2, Hash: "hash-2"}); err != nil {
		t.Fatalf("Save a upsert: %v", err)
	}

	got, err = heads.List()
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(got) != 2 {
		t.Fatalf("head count = %d, want 2 (upsert must not add a row)", len(got))
	}
	if got["issuer-a"] != (trust.Head{Seq: 2, Hash: "hash-2"}) {
		t.Errorf("issuer-a head = %+v, want {2 hash-2}", got["issuer-a"])
	}
	if got["issuer-b"] != (trust.Head{Seq: 5, Hash: "hash-b"}) {
		t.Errorf("issuer-b head = %+v, want {5 hash-b}", got["issuer-b"])
	}
}
