package config

import (
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// writeConfig writes content to a config.yaml inside a fresh temp dir and
// returns its path.
func writeConfig(t *testing.T, content string) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), "config.yaml")
	if err := os.WriteFile(path, []byte(content), 0o600); err != nil {
		t.Fatalf("writing config fixture: %v", err)
	}
	return path
}

// setHome points HOME/USERPROFILE at a fresh temp dir so path resolution is
// deterministic on every platform. It returns the directory.
func setHome(t *testing.T) string {
	t.Helper()
	home := t.TempDir()
	t.Setenv("HOME", home)
	t.Setenv("USERPROFILE", home) // Windows
	return home
}

func TestDefault(t *testing.T) {
	want := Config{SecretDB: DefaultSecretDB}
	if got := *Default(); got != want {
		t.Errorf("Default() = %+v, want %+v", got, want)
	}
}

func TestDefaultPath(t *testing.T) {
	home := setHome(t)

	path, err := defaultPath()
	if err != nil {
		t.Fatalf("defaultPath returned error: %v", err)
	}
	if want := filepath.Join(home, ".goph", "config.yaml"); path != want {
		t.Errorf("defaultPath() = %q, want %q", path, want)
	}
}

func TestResolveSecretDB(t *testing.T) {
	home := setHome(t)

	tests := []struct {
		name    string
		in      string
		want    string
		wantErr bool
	}{
		{"tilde slash expands", "~/secrets.db", filepath.Join(home, "secrets.db"), false},
		{"bare tilde expands to home", "~", home, false},
		{"absolute path kept", filepath.Join(home, "abs.db"), filepath.Join(home, "abs.db"), false},
		{"relative path kept", "secrets.db", "secrets.db", false},
		{"user form rejected", "~bob/secrets.db", "", true},
		{"empty rejected", "", "", true},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, err := (&Config{SecretDB: tc.in}).ResolveSecretDB()
			if tc.wantErr {
				if err == nil {
					t.Fatalf("expected error for %q, got nil", tc.in)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if got != tc.want {
				t.Errorf("ResolveSecretDB(%q) = %q, want %q", tc.in, got, tc.want)
			}
		})
	}
}

func TestFileStore_Load_Valid(t *testing.T) {
	tests := []struct {
		name string
		yaml string
		want Config
	}{
		{
			name: "all fields set",
			yaml: "remote: https://example.com\nsecret-db: ~/db.sqlite\ndevice-name: laptop\ndefault-folder: work\n",
			want: Config{
				Remote:        "https://example.com",
				SecretDB:      "~/db.sqlite",
				DeviceName:    "laptop",
				DefaultFolder: "work",
			},
		},
		{
			name: "secret-db defaults when omitted",
			yaml: "remote: https://example.com\ndevice-name: laptop\n",
			want: Config{Remote: "https://example.com", DeviceName: "laptop", SecretDB: DefaultSecretDB},
		},
		{
			name: "empty file yields defaults",
			yaml: "",
			want: Config{SecretDB: DefaultSecretDB},
		},
		{
			name: "comments only yields defaults",
			yaml: "# nothing but a comment\n",
			want: Config{SecretDB: DefaultSecretDB},
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			cfg, err := NewFileStore(writeConfig(t, tc.yaml)).Load()
			if err != nil {
				t.Fatalf("Load returned error: %v", err)
			}
			if *cfg != tc.want {
				t.Errorf("Load = %+v, want %+v", *cfg, tc.want)
			}
		})
	}
}

// Decoding on top of the defaults means an omitted or null secret-db keeps the
// default, while an explicit empty string overrides it — so callers can tell
// "unset" from "deliberately empty".
func TestFileStore_Load_SecretDBDefaulting(t *testing.T) {
	tests := []struct {
		name string
		yaml string
		want string
	}{
		{"omitted keeps default", "remote: https://x\n", DefaultSecretDB},
		{"null keeps default", "secret-db:\n", DefaultSecretDB},
		{"explicit empty overrides", `secret-db: ""` + "\n", ""},
		{"explicit value overrides", "secret-db: ~/db.sqlite\n", "~/db.sqlite"},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			cfg, err := NewFileStore(writeConfig(t, tc.yaml)).Load()
			if err != nil {
				t.Fatalf("Load returned error: %v", err)
			}
			if cfg.SecretDB != tc.want {
				t.Errorf("SecretDB = %q, want %q", cfg.SecretDB, tc.want)
			}
		})
	}
}

func TestFileStore_Load_Errors(t *testing.T) {
	tests := []struct {
		name string
		yaml string
	}{
		{"malformed yaml", "this is not yaml: [}"},
		{"unknown field", "remote: https://example.com\ntypo-field: nope\n"},
		{"wrong type for remote", "remote: [a, b, c]\n"},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			if _, err := NewFileStore(writeConfig(t, tc.yaml)).Load(); err == nil {
				t.Error("expected error, got nil")
			}
		})
	}
}

// The unknown-field error must name the offending key so the user can fix it.
func TestFileStore_Load_UnknownFieldIsNamed(t *testing.T) {
	_, err := NewFileStore(writeConfig(t, "bogus-key: x\n")).Load()
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !strings.Contains(err.Error(), "bogus-key") {
		t.Errorf("error %q should name the offending field", err)
	}
}

// A missing file must surface as ErrConfigNotFound so callers can bootstrap a
// default config instead of failing.
func TestFileStore_Load_NotFound(t *testing.T) {
	path := filepath.Join(t.TempDir(), "missing.yaml")

	_, err := NewFileStore(path).Load()
	if err == nil {
		t.Fatal("expected error for missing file, got nil")
	}
	if !errors.Is(err, ErrConfigNotFound) {
		t.Errorf("error %v does not wrap ErrConfigNotFound", err)
	}
}

func TestFileStore_Save_CreatesFileAndParentDir(t *testing.T) {
	path := filepath.Join(t.TempDir(), ".goph", "config.yaml")
	cfg := &Config{Remote: "https://test.com", SecretDB: "~/my.db"}

	if err := NewFileStore(path).Save(cfg); err != nil {
		t.Fatalf("Save returned error: %v", err)
	}
	if _, err := os.Stat(path); err != nil {
		t.Fatalf("config file not created: %v", err)
	}
	if _, err := os.Stat(filepath.Dir(path)); err != nil {
		t.Fatalf("parent directory not created: %v", err)
	}
}

// Save then Load through the default store must reproduce the config exactly,
// and Save must create the .goph directory along the way.
func TestSaveLoadRoundTrip(t *testing.T) {
	setHome(t)

	store, err := DefaultStore()
	if err != nil {
		t.Fatalf("DefaultStore returned error: %v", err)
	}

	want := &Config{
		Remote:        "https://api.example.com",
		SecretDB:      "~/goph/secrets.db",
		DeviceName:    "test-machine",
		DefaultFolder: "personal",
	}

	if err := store.Save(want); err != nil {
		t.Fatalf("Save returned error: %v", err)
	}
	got, err := store.Load()
	if err != nil {
		t.Fatalf("Load returned error: %v", err)
	}
	if *got != *want {
		t.Errorf("round trip mismatch:\n got %+v\nwant %+v", *got, *want)
	}
}

func TestDefaultStore_Load_NotFound(t *testing.T) {
	setHome(t)

	store, err := DefaultStore()
	if err != nil {
		t.Fatalf("DefaultStore returned error: %v", err)
	}
	if _, err := store.Load(); !errors.Is(err, ErrConfigNotFound) {
		t.Errorf("error %v does not wrap ErrConfigNotFound", err)
	}
}
