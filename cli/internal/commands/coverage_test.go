package commands

import (
	"bytes"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/spf13/cobra"

	"github.com/svetlana1959/GophKeeper/cli/internal/app"
)

// runIn is like run but feeds stdin to the command tree. cobra propagates
// SetIn to subcommands via InOrStdin, so prompts/piped values are readable.
func runIn(t *testing.T, stdin string, args ...string) (string, error) {
	t.Helper()
	root := newRootCmd()
	var buf bytes.Buffer
	root.SetOut(&buf)
	root.SetErr(&buf)
	root.SetIn(strings.NewReader(stdin))
	root.SetArgs(args)
	err := root.Execute()
	return buf.String(), err
}

// initBasic sets up an isolated home and a non-PIN vault.
func initBasic(t *testing.T) {
	t.Helper()
	setHome(t)
	if out, err := run(t, "init", "--device-name", "test"); err != nil {
		t.Fatalf("init: %v\n%s", err, out)
	}
}

// --- confirm (delete without --force) ---------------------------------------

func TestDelete_ConfirmYes(t *testing.T) {
	initBasic(t)
	if _, err := run(t, "set", "gh", "--value", "tok"); err != nil {
		t.Fatalf("set: %v", err)
	}

	out, err := runIn(t, "y\n", "delete", "gh")
	if err != nil {
		t.Fatalf("delete: %v\n%s", err, out)
	}
	if !strings.Contains(out, "Deleted") {
		t.Errorf("delete output = %q, want to contain Deleted", out)
	}
	if _, err := run(t, "get", "gh"); !errors.Is(err, app.ErrSecretNotFound) {
		t.Errorf("get after confirmed delete err = %v, want ErrSecretNotFound", err)
	}
}

func TestDelete_ConfirmNo(t *testing.T) {
	initBasic(t)
	if _, err := run(t, "set", "gh", "--value", "tok"); err != nil {
		t.Fatalf("set: %v", err)
	}

	out, err := runIn(t, "n\n", "delete", "gh")
	if err != nil {
		t.Fatalf("delete: %v\n%s", err, out)
	}
	if !strings.Contains(out, "Aborted") {
		t.Errorf("delete output = %q, want to contain Aborted", out)
	}
	// Secret must still be readable.
	got, err := run(t, "get", "gh")
	if err != nil {
		t.Fatalf("get after aborted delete: %v", err)
	}
	if strings.TrimSpace(got) != "tok" {
		t.Errorf("get = %q, want tok", got)
	}
}

func TestDelete_ConfirmNoTrailingNewline(t *testing.T) {
	initBasic(t)
	if _, err := run(t, "set", "gh", "--value", "tok"); err != nil {
		t.Fatalf("set: %v", err)
	}
	// "y" with no trailing newline: readLine consumes to EOF and still answers.
	out, err := runIn(t, "y", "delete", "gh")
	if err != nil {
		t.Fatalf("delete: %v\n%s", err, out)
	}
	if !strings.Contains(out, "Deleted") {
		t.Errorf("delete output = %q, want Deleted", out)
	}
}

func TestDelete_ConfirmEmptyDefaultsNo(t *testing.T) {
	initBasic(t)
	if _, err := run(t, "set", "gh", "--value", "tok"); err != nil {
		t.Fatalf("set: %v", err)
	}
	// Empty line defaults to "no".
	out, err := runIn(t, "\n", "delete", "gh")
	if err != nil {
		t.Fatalf("delete: %v\n%s", err, out)
	}
	if !strings.Contains(out, "Aborted") {
		t.Errorf("delete output = %q, want Aborted", out)
	}
}

// --- readValue: --file and piped stdin --------------------------------------

func TestSet_FromFile(t *testing.T) {
	initBasic(t)
	dir := t.TempDir()
	path := filepath.Join(dir, "secret.txt")
	// Content includes a trailing newline; --file stores bytes verbatim.
	if err := os.WriteFile(path, []byte("filesecret\n"), 0o600); err != nil {
		t.Fatalf("write file: %v", err)
	}

	if out, err := run(t, "set", "fromfile", "--file", path); err != nil {
		t.Fatalf("set --file: %v\n%s", err, out)
	}

	got, err := run(t, "get", "fromfile")
	if err != nil {
		t.Fatalf("get: %v", err)
	}
	// get appends its own newline; the stored value keeps the file's newline.
	if got != "filesecret\n\n" {
		t.Errorf("get = %q, want %q", got, "filesecret\n\n")
	}
}

func TestSet_FromFileMissing(t *testing.T) {
	initBasic(t)
	if _, err := run(t, "set", "x", "--file", filepath.Join(t.TempDir(), "nope.txt")); err == nil {
		t.Errorf("set --file with missing file: want error, got nil")
	}
}

func TestSet_FromStdin(t *testing.T) {
	initBasic(t)
	// A single trailing newline is stripped from piped stdin.
	if out, err := runIn(t, "pipedsecret\n", "set", "piped"); err != nil {
		t.Fatalf("set stdin: %v\n%s", err, out)
	}

	got, err := run(t, "get", "piped")
	if err != nil {
		t.Fatalf("get: %v", err)
	}
	if strings.TrimSpace(got) != "pipedsecret" {
		t.Errorf("get = %q, want pipedsecret", got)
	}
}

func TestSet_EmptyValueFlagHonored(t *testing.T) {
	initBasic(t)
	// An explicit empty --value is honored (Changed is true).
	if out, err := run(t, "set", "empty", "--value", ""); err != nil {
		t.Fatalf("set empty: %v\n%s", err, out)
	}
	got, err := run(t, "get", "empty")
	if err != nil {
		t.Fatalf("get: %v", err)
	}
	if got != "\n" {
		t.Errorf("get = %q, want a lone newline", got)
	}
}

// --- get --field ------------------------------------------------------------

func TestGet_Field(t *testing.T) {
	initBasic(t)
	if _, err := run(t, "set", "gh", "--value", "tok", "--description", "my desc"); err != nil {
		t.Fatalf("set: %v", err)
	}

	out, err := run(t, "get", "gh", "--field", "description")
	if err != nil {
		t.Fatalf("get --field: %v", err)
	}
	if strings.TrimSpace(out) != "my desc" {
		t.Errorf("get --field description = %q, want 'my desc'", out)
	}

	if _, err := run(t, "get", "gh", "--field", "nope"); !errors.Is(err, app.ErrFieldNotFound) {
		t.Errorf("get --field nope err = %v, want ErrFieldNotFound", err)
	}
}

func TestGet_Nonexistent(t *testing.T) {
	initBasic(t)
	if _, err := run(t, "get", "ghost"); !errors.Is(err, app.ErrSecretNotFound) {
		t.Errorf("get nonexistent err = %v, want ErrSecretNotFound", err)
	}
}

func TestDelete_Nonexistent(t *testing.T) {
	initBasic(t)
	if _, err := run(t, "delete", "ghost", "--force"); !errors.Is(err, app.ErrSecretNotFound) {
		t.Errorf("delete nonexistent err = %v, want ErrSecretNotFound", err)
	}
}

// --- list variants ----------------------------------------------------------

func TestList_Empty(t *testing.T) {
	initBasic(t)
	out, err := run(t, "list")
	if err != nil {
		t.Fatalf("list: %v", err)
	}
	if !strings.Contains(out, "No secrets yet") {
		t.Errorf("list empty = %q, want 'No secrets yet'", out)
	}
}

func TestList_JSON(t *testing.T) {
	initBasic(t)
	if _, err := run(t, "set", "gh", "--value", "tok", "--folder", "work"); err != nil {
		t.Fatalf("set: %v", err)
	}
	out, err := run(t, "list", "--json")
	if err != nil {
		t.Fatalf("list --json: %v", err)
	}
	if !strings.Contains(out, "\"name\"") || !strings.Contains(out, "gh") {
		t.Errorf("list --json = %q, want JSON mentioning gh", out)
	}
}

func TestList_FolderFilterAndAll(t *testing.T) {
	initBasic(t)
	if _, err := run(t, "set", "a", "--value", "1", "--folder", "work"); err != nil {
		t.Fatalf("set a: %v", err)
	}
	if _, err := run(t, "set", "b", "--value", "2", "--folder", "home"); err != nil {
		t.Fatalf("set b: %v", err)
	}
	if _, err := run(t, "delete", "b", "--force"); err != nil {
		t.Fatalf("delete b: %v", err)
	}

	// Folder filter: only work items.
	out, err := run(t, "list", "--folder", "work")
	if err != nil {
		t.Fatalf("list --folder: %v", err)
	}
	if !strings.Contains(out, "a") || strings.Contains(out, "\nb ") {
		t.Errorf("list --folder work = %q, want a only", out)
	}

	// --all includes the soft-deleted b (status deleted).
	out, err = run(t, "list", "--all")
	if err != nil {
		t.Fatalf("list --all: %v", err)
	}
	if !strings.Contains(out, "deleted") {
		t.Errorf("list --all = %q, want a deleted status", out)
	}
}

// --- init edge cases --------------------------------------------------------

func TestInit_AlreadyInitialized(t *testing.T) {
	initBasic(t)
	if _, err := run(t, "init", "--device-name", "again"); !errors.Is(err, app.ErrAlreadyInitialized) {
		t.Errorf("re-init err = %v, want ErrAlreadyInitialized", err)
	}
}

func TestInit_Force(t *testing.T) {
	initBasic(t)
	if out, err := run(t, "init", "--device-name", "again", "--force"); err != nil {
		t.Fatalf("init --force: %v\n%s", err, out)
	}
}

func TestInit_DefaultsToHostname(t *testing.T) {
	setHome(t)
	out, err := run(t, "init")
	if err != nil {
		t.Fatalf("init without device-name: %v\n%s", err, out)
	}
	if !strings.Contains(out, "Initialized device") {
		t.Errorf("init output = %q, want 'Initialized device'", out)
	}
}

func TestInit_KeyFileMissing(t *testing.T) {
	setHome(t)
	if _, err := run(t, "init", "--key-file", filepath.Join(t.TempDir(), "nope.key")); err == nil {
		t.Errorf("init --key-file missing: want error, got nil")
	}
}

// --- PIN flow (init.go readNewPIN, get PIN prompt, promptHidden non-tty) -----

func TestPIN_RoundTrip(t *testing.T) {
	setHome(t)
	// init --pin prompts twice.
	if out, err := runIn(t, "1234\n1234\n", "init", "--device-name", "p", "--pin"); err != nil {
		t.Fatalf("init --pin: %v\n%s", err, out)
	}

	// set does not require a PIN (encrypts to the public key).
	if out, err := run(t, "set", "gh", "--value", "tok"); err != nil {
		t.Fatalf("set: %v\n%s", err, out)
	}

	// get requires the PIN.
	out, err := runIn(t, "1234\n", "get", "gh")
	if err != nil {
		t.Fatalf("get with PIN: %v\n%s", err, out)
	}
	if !strings.Contains(out, "tok") {
		t.Errorf("get with PIN = %q, want tok", out)
	}
}

func TestPIN_WrongOnGet(t *testing.T) {
	setHome(t)
	if out, err := runIn(t, "1234\n1234\n", "init", "--device-name", "p", "--pin"); err != nil {
		t.Fatalf("init --pin: %v\n%s", err, out)
	}
	if _, err := run(t, "set", "gh", "--value", "tok"); err != nil {
		t.Fatalf("set: %v", err)
	}
	if _, err := runIn(t, "9999\n", "get", "gh"); !errors.Is(err, app.ErrWrongPIN) {
		t.Errorf("get with wrong PIN err = %v, want ErrWrongPIN", err)
	}
}

func TestPIN_MismatchAtInit(t *testing.T) {
	setHome(t)
	_, err := runIn(t, "1234\n5678\n", "init", "--device-name", "p", "--pin")
	if err == nil || !strings.Contains(err.Error(), "do not match") {
		t.Errorf("init --pin mismatch err = %v, want 'PINs do not match'", err)
	}
}

func TestPIN_EmptyAtInit(t *testing.T) {
	setHome(t)
	_, err := runIn(t, "\n\n", "init", "--device-name", "p", "--pin")
	if err == nil || !strings.Contains(err.Error(), "must not be empty") {
		t.Errorf("init --pin empty err = %v, want 'PIN must not be empty'", err)
	}
}

// --- pinIfNeeded (root.go) directly -----------------------------------------

func TestPinIfNeeded(t *testing.T) {
	setHome(t)

	// Non-PIN vault: returns "" without reading input.
	if _, err := run(t, "init", "--device-name", "np"); err != nil {
		t.Fatalf("init: %v", err)
	}
	sess, err := app.Open()
	if err != nil {
		t.Fatalf("open: %v", err)
	}
	cmd := &cobra.Command{}
	cmd.SetOut(&bytes.Buffer{})
	cmd.SetIn(strings.NewReader(""))
	pin, err := pinIfNeeded(cmd, sess)
	sess.Close()
	if err != nil || pin != "" {
		t.Errorf("pinIfNeeded (no PIN) = %q, %v; want \"\", nil", pin, err)
	}

	// PIN vault: prompts and returns the piped PIN.
	setHome(t)
	if _, err := runIn(t, "4321\n4321\n", "init", "--device-name", "pp", "--pin"); err != nil {
		t.Fatalf("init --pin: %v", err)
	}
	sess2, err := app.Open()
	if err != nil {
		t.Fatalf("open: %v", err)
	}
	defer sess2.Close()
	cmd2 := &cobra.Command{}
	cmd2.SetOut(&bytes.Buffer{})
	cmd2.SetIn(strings.NewReader("4321\n"))
	pin, err = pinIfNeeded(cmd2, sess2)
	if err != nil {
		t.Fatalf("pinIfNeeded (PIN): %v", err)
	}
	if pin != "4321" {
		t.Errorf("pinIfNeeded (PIN) = %q, want 4321", pin)
	}
}

// --- offline wrappers for networked commands --------------------------------
//
// With no remote configured, app.connect (and ListDevices' local sync-state
// check) fail fast without dialing, so these command wrappers — withSession,
// pinIfNeeded, and the closure body up to the error return — run hermetically.

func TestSync_NoRemote(t *testing.T) {
	initBasic(t)
	if _, err := run(t, "sync"); !errors.Is(err, app.ErrNoRemote) {
		t.Errorf("sync without remote err = %v, want ErrNoRemote", err)
	}
}

func TestLink_NoRemote(t *testing.T) {
	initBasic(t)
	if _, err := run(t, "link", "somecode"); !errors.Is(err, app.ErrNoRemote) {
		t.Errorf("link without remote err = %v, want ErrNoRemote", err)
	}
}

func TestDeviceInvite_NoRemote(t *testing.T) {
	initBasic(t)
	if _, err := run(t, "device", "invite"); !errors.Is(err, app.ErrNoRemote) {
		t.Errorf("device invite without remote err = %v, want ErrNoRemote", err)
	}
}

func TestDeviceRevoke_NoRemote(t *testing.T) {
	initBasic(t)
	if _, err := run(t, "device", "revoke", "dev-1"); !errors.Is(err, app.ErrNoRemote) {
		t.Errorf("device revoke without remote err = %v, want ErrNoRemote", err)
	}
}

func TestDeviceLs_NotLinked(t *testing.T) {
	initBasic(t)
	// A freshly-initialized device has no sync state yet.
	if _, err := run(t, "device", "ls"); !errors.Is(err, app.ErrNotLinked) {
		t.Errorf("device ls before link err = %v, want ErrNotLinked", err)
	}
}

// --- shortKey (device.go) ---------------------------------------------------

func TestShortKey(t *testing.T) {
	short := "age1short"
	if got := shortKey(short); got != short {
		t.Errorf("shortKey(short) = %q, want unchanged %q", got, short)
	}

	boundary := strings.Repeat("x", 20)
	if got := shortKey(boundary); got != boundary {
		t.Errorf("shortKey(len=20) = %q, want unchanged", got)
	}

	long := strings.Repeat("y", 40)
	got := shortKey(long)
	if got != long[:20]+"…" {
		t.Errorf("shortKey(long) = %q, want truncated with ellipsis", got)
	}
	if !strings.HasSuffix(got, "…") {
		t.Errorf("shortKey(long) = %q, want trailing ellipsis", got)
	}
}
