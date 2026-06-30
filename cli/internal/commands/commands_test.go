package commands

import (
	"bytes"
	"errors"
	"strings"
	"testing"

	"github.com/svetlana1959/GophKeeper/cli/internal/app"
)

func setHome(t *testing.T) {
	t.Helper()
	dir := t.TempDir()
	t.Setenv("HOME", dir)
	t.Setenv("USERPROFILE", dir)
}

// run executes the goph command tree with args, capturing combined output.
func run(t *testing.T, args ...string) (string, error) {
	t.Helper()
	root := newRootCmd()
	var buf bytes.Buffer
	root.SetOut(&buf)
	root.SetErr(&buf)
	root.SetArgs(args)
	err := root.Execute()
	return buf.String(), err
}

func TestCommands_EndToEnd(t *testing.T) {
	setHome(t)

	if out, err := run(t, "init", "--device-name", "test"); err != nil {
		t.Fatalf("init: %v\n%s", err, out)
	}

	if out, err := run(t, "set", "gh", "--value", "tok", "--folder", "work"); err != nil {
		t.Fatalf("set: %v\n%s", err, out)
	}

	out, err := run(t, "get", "gh")
	if err != nil {
		t.Fatalf("get: %v", err)
	}
	if strings.TrimSpace(out) != "tok" {
		t.Errorf("get output = %q, want tok", out)
	}

	out, err = run(t, "list")
	if err != nil {
		t.Fatalf("list: %v", err)
	}
	if !strings.Contains(out, "gh") || !strings.Contains(out, "work") {
		t.Errorf("list output = %q, want to mention gh/work", out)
	}

	if out, err := run(t, "delete", "gh", "--force"); err != nil {
		t.Fatalf("delete: %v\n%s", err, out)
	}
	if _, err := run(t, "get", "gh"); !errors.Is(err, app.ErrSecretNotFound) {
		t.Errorf("get after delete err = %v, want ErrSecretNotFound", err)
	}
}

func TestCommands_NotInitialized(t *testing.T) {
	setHome(t)

	if _, err := run(t, "list"); !errors.Is(err, app.ErrNotInitialized) {
		t.Errorf("list without init err = %v, want ErrNotInitialized", err)
	}
}
