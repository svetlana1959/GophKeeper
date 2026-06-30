//go:build unix

package config

import (
	"os"
	"path/filepath"
	"testing"
)

// On Unix the config may hold a remote URL and device identity, so the adapter
// must persist the directory as 0700 and the file as 0600 — never group- or
// world-readable. Windows has no equivalent mode bits; there the cross-platform
// round-trip tests cover persistence instead.
func TestFileStore_Save_UnixPermissions(t *testing.T) {
	path := filepath.Join(t.TempDir(), ".goph", "config.yaml")
	cfg := &Config{Remote: "https://test.com", SecretDB: "~/my.db"}

	if err := NewFileStore(path).Save(cfg); err != nil {
		t.Fatalf("Save returned error: %v", err)
	}

	fileInfo, err := os.Stat(path)
	if err != nil {
		t.Fatalf("stat file: %v", err)
	}
	if got := fileInfo.Mode().Perm(); got != 0o600 {
		t.Errorf("file mode = %v, want 0600", got)
	}

	dirInfo, err := os.Stat(filepath.Dir(path))
	if err != nil {
		t.Fatalf("stat dir: %v", err)
	}
	if got := dirInfo.Mode().Perm(); got != 0o700 {
		t.Errorf("dir mode = %v, want 0700", got)
	}
}
