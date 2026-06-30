package app_test

import (
	"bytes"
	"errors"
	"testing"

	"github.com/svetlana1959/GophKeeper/cli/internal/app"
	"github.com/svetlana1959/GophKeeper/cli/internal/crypto"
)

// setHome isolates config + vault under a temp HOME so each test is independent.
func setHome(t *testing.T) {
	t.Helper()
	dir := t.TempDir()
	t.Setenv("HOME", dir)
	t.Setenv("USERPROFILE", dir) // Windows
}

func initAndOpen(t *testing.T, p app.InitParams) *app.Session {
	t.Helper()
	if _, err := app.Init(p); err != nil {
		t.Fatalf("Init: %v", err)
	}
	sess, err := app.Open()
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	t.Cleanup(func() { sess.Close() })
	return sess
}

func TestInit_ResultAndOpen(t *testing.T) {
	setHome(t)

	res, err := app.Init(app.InitParams{DeviceName: "laptop"})
	if err != nil {
		t.Fatalf("Init: %v", err)
	}
	if res.DeviceID == "" || res.PublicKey == "" {
		t.Errorf("Init result = %+v, want non-empty fields", res)
	}

	sess, err := app.Open()
	if err != nil {
		t.Fatalf("Open after init: %v", err)
	}
	defer sess.Close()
	if sess.NeedsPIN() {
		t.Error("NeedsPIN = true, want false for plaintext key")
	}
}

func TestInit_RefusesExistingUnlessForce(t *testing.T) {
	setHome(t)

	if _, err := app.Init(app.InitParams{DeviceName: "a"}); err != nil {
		t.Fatalf("first Init: %v", err)
	}
	if _, err := app.Init(app.InitParams{DeviceName: "b"}); !errors.Is(err, app.ErrAlreadyInitialized) {
		t.Errorf("second Init err = %v, want ErrAlreadyInitialized", err)
	}
	if _, err := app.Init(app.InitParams{DeviceName: "b", Force: true}); err != nil {
		t.Errorf("forced Init: %v", err)
	}
}

func TestInit_ImportKey(t *testing.T) {
	setHome(t)

	kp, err := crypto.GenerateKeyPair()
	if err != nil {
		t.Fatalf("GenerateKeyPair: %v", err)
	}
	res, err := app.Init(app.InitParams{DeviceName: "d", PrivateKey: kp.Private})
	if err != nil {
		t.Fatalf("Init import: %v", err)
	}
	if res.PublicKey != kp.Public {
		t.Errorf("imported PublicKey = %q, want %q", res.PublicKey, kp.Public)
	}
}

func TestOpen_NotInitialized(t *testing.T) {
	setHome(t)

	if _, err := app.Open(); !errors.Is(err, app.ErrNotInitialized) {
		t.Errorf("Open err = %v, want ErrNotInitialized", err)
	}
}

func TestSetGet_RoundTrip(t *testing.T) {
	setHome(t)
	sess := initAndOpen(t, app.InitParams{DeviceName: "d"})

	if err := sess.Set(app.SetParams{Name: "gh", Value: []byte("token"), Description: "github PAT"}); err != nil {
		t.Fatalf("Set: %v", err)
	}

	got, err := sess.Get("gh", "", "")
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if string(got) != "token" {
		t.Errorf("Get value = %q, want token", got)
	}

	desc, err := sess.Get("gh", "", "description")
	if err != nil {
		t.Fatalf("Get field: %v", err)
	}
	if string(desc) != "github PAT" {
		t.Errorf("Get description = %q, want 'github PAT'", desc)
	}

	if _, err := sess.Get("gh", "", "missing"); !errors.Is(err, app.ErrFieldNotFound) {
		t.Errorf("Get missing field err = %v, want ErrFieldNotFound", err)
	}
}

// Binary (non-UTF-8) values must survive the JSON round-trip intact.
func TestSetGet_BinaryValue(t *testing.T) {
	setHome(t)
	sess := initAndOpen(t, app.InitParams{DeviceName: "d"})

	want := []byte{0x00, 0xff, 0xfe, 0x01, 0x80, 0x7f}
	if err := sess.Set(app.SetParams{Name: "bin", Value: want}); err != nil {
		t.Fatalf("Set: %v", err)
	}
	got, err := sess.Get("bin", "", "")
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if !bytes.Equal(got, want) {
		t.Errorf("Get = %x, want %x", got, want)
	}
}

func TestGet_NotFound(t *testing.T) {
	setHome(t)
	sess := initAndOpen(t, app.InitParams{DeviceName: "d"})

	if _, err := sess.Get("nope", "", ""); !errors.Is(err, app.ErrSecretNotFound) {
		t.Errorf("Get err = %v, want ErrSecretNotFound", err)
	}
}

func TestSet_UpdateBumpsVersion(t *testing.T) {
	setHome(t)
	sess := initAndOpen(t, app.InitParams{DeviceName: "d"})

	if err := sess.Set(app.SetParams{Name: "k", Value: []byte("v1")}); err != nil {
		t.Fatalf("create: %v", err)
	}
	if err := sess.Set(app.SetParams{Name: "k", Value: []byte("v2")}); err != nil {
		t.Fatalf("update: %v", err)
	}

	got, err := sess.Get("k", "", "")
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if string(got) != "v2" {
		t.Errorf("value = %q, want v2", got)
	}

	items, err := sess.List("", false)
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(items) != 1 || items[0].Version != 2 {
		t.Errorf("items = %+v, want one at version 2", items)
	}
}

func TestDelete_TombstonesAndHides(t *testing.T) {
	setHome(t)
	sess := initAndOpen(t, app.InitParams{DeviceName: "d"})

	if err := sess.Set(app.SetParams{Name: "k", Value: []byte("v")}); err != nil {
		t.Fatalf("Set: %v", err)
	}
	if err := sess.Delete("k"); err != nil {
		t.Fatalf("Delete: %v", err)
	}

	if _, err := sess.Get("k", "", ""); !errors.Is(err, app.ErrSecretNotFound) {
		t.Errorf("Get after delete err = %v, want ErrSecretNotFound", err)
	}
	if err := sess.Delete("k"); !errors.Is(err, app.ErrSecretNotFound) {
		t.Errorf("re-Delete err = %v, want ErrSecretNotFound", err)
	}

	if items, _ := sess.List("", false); len(items) != 0 {
		t.Errorf("List(active) = %+v, want empty", items)
	}
	all, _ := sess.List("", true)
	if len(all) != 1 || !all[0].Deleted {
		t.Errorf("List(all) = %+v, want one deleted", all)
	}
}

func TestList_EmptyAndFolderFilter(t *testing.T) {
	setHome(t)
	sess := initAndOpen(t, app.InitParams{DeviceName: "d"})

	if items, _ := sess.List("", false); len(items) != 0 {
		t.Errorf("empty store List = %+v, want empty", items)
	}

	mustSet(t, sess, app.SetParams{Name: "a", Value: []byte("1"), Folder: "work"})
	mustSet(t, sess, app.SetParams{Name: "b", Value: []byte("2"), Folder: "home"})

	work, err := sess.List("work", false)
	if err != nil {
		t.Fatalf("List folder: %v", err)
	}
	if len(work) != 1 || work[0].Name != "a" {
		t.Errorf("List(work) = %+v, want only a", work)
	}
}

func TestPINProtectedKey(t *testing.T) {
	setHome(t)
	sess := initAndOpen(t, app.InitParams{DeviceName: "d", PIN: "1234"})

	if !sess.NeedsPIN() {
		t.Fatal("NeedsPIN = false, want true")
	}
	if err := sess.Set(app.SetParams{Name: "s", Value: []byte("v")}); err != nil {
		t.Fatalf("Set: %v", err) // Set seals to the public key; no PIN needed
	}

	if got, err := sess.Get("s", "1234", ""); err != nil || string(got) != "v" {
		t.Fatalf("Get with PIN = %q, %v", got, err)
	}
	if _, err := sess.Get("s", "9999", ""); !errors.Is(err, app.ErrWrongPIN) {
		t.Errorf("wrong PIN err = %v, want ErrWrongPIN", err)
	}
	if _, err := sess.Get("s", "", ""); !errors.Is(err, app.ErrPINRequired) {
		t.Errorf("no PIN err = %v, want ErrPINRequired", err)
	}
}

func mustSet(t *testing.T, sess *app.Session, p app.SetParams) {
	t.Helper()
	if err := sess.Set(p); err != nil {
		t.Fatalf("Set %q: %v", p.Name, err)
	}
}
