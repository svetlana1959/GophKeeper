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
	if err := os.WriteFile(path, []byte(content), 0600); err != nil {
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

func TestConfigPath(t *testing.T) {
	home := setHome(t)

	path, err := ConfigPath()
	if err != nil {
		t.Fatalf("ConfigPath returned error: %v", err)
	}
	if want := filepath.Join(home, ".goph", "config.yaml"); path != want {
		t.Errorf("ConfigPath() = %q, want %q", path, want)
	}
}

func TestDefault(t *testing.T) {
	want := Config{SecretDB: DefaultSecretDB}
	if got := *Default(); got != want {
		t.Errorf("Default() = %+v, want %+v", got, want)
	}
}

func TestLoadFromFile_SecretDBDefaulting(t *testing.T) {
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
			cfg, err := LoadFromFile(writeConfig(t, tc.yaml))
			if err != nil {
				t.Fatalf("LoadFromFile returned error: %v", err)
			}
			if cfg.SecretDB != tc.want {
				t.Errorf("SecretDB = %q, want %q", cfg.SecretDB, tc.want)
			}
		})
	}
}

func TestLoadFromFile_Valid(t *testing.T) {
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
			cfg, err := LoadFromFile(writeConfig(t, tc.yaml))
			if err != nil {
				t.Fatalf("LoadFromFile returned error: %v", err)
			}
			if *cfg != tc.want {
				t.Errorf("LoadFromFile = %+v, want %+v", *cfg, tc.want)
			}
		})
	}
}

func TestLoadFromFile_Errors(t *testing.T) {
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
			if _, err := LoadFromFile(writeConfig(t, tc.yaml)); err == nil {
				t.Error("expected error, got nil")
			}
		})
	}
}

// The unknown-field error must name the offending key so the user can fix it.
func TestLoadFromFile_UnknownFieldIsNamed(t *testing.T) {
	_, err := LoadFromFile(writeConfig(t, "bogus-key: x\n"))
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !strings.Contains(err.Error(), "bogus-key") {
		t.Errorf("error %q should name the offending field", err)
	}
}

// Callers detect a missing config with errors.Is(err, os.ErrNotExist); the
// adapter must preserve that wrapping.
func TestLoadFromFile_NotFound(t *testing.T) {
	path := filepath.Join(t.TempDir(), "missing.yaml")

	_, err := LoadFromFile(path)
	if err == nil {
		t.Fatal("expected error for missing file, got nil")
	}
	if !errors.Is(err, os.ErrNotExist) {
		t.Errorf("error %v does not wrap os.ErrNotExist", err)
	}
}

func TestValidateForSync(t *testing.T) {
	if err := (&Config{Remote: ""}).ValidateForSync(); err == nil {
		t.Error("expected error when remote is empty")
	}
	if err := (&Config{Remote: "https://valid.com"}).ValidateForSync(); err != nil {
		t.Errorf("unexpected error: %v", err)
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

func TestSaveToFile_CreatesFileAndParentDir(t *testing.T) {
	path := filepath.Join(t.TempDir(), ".goph", "config.yaml")
	cfg := &Config{Remote: "https://test.com", SecretDB: "~/my.db"}

	if err := cfg.SaveToFile(path); err != nil {
		t.Fatalf("SaveToFile returned error: %v", err)
	}
	if _, err := os.Stat(path); err != nil {
		t.Fatalf("config file not created: %v", err)
	}
	if _, err := os.Stat(filepath.Dir(path)); err != nil {
		t.Fatalf("parent directory not created: %v", err)
	}
}

// Save then Load through the default path must reproduce the config exactly,
// and Save must create the .goph directory along the way.
func TestSaveLoadRoundTrip(t *testing.T) {
	setHome(t)

	want := &Config{
		Remote:        "https://api.example.com",
		SecretDB:      "~/goph/secrets.db",
		DeviceName:    "test-machine",
		DefaultFolder: "personal",
	}

	if err := want.Save(); err != nil {
		t.Fatalf("Save returned error: %v", err)
	}
	got, err := Load()
	if err != nil {
		t.Fatalf("Load returned error: %v", err)
	}
	if *got != *want {
		t.Errorf("round trip mismatch:\n got %+v\nwant %+v", *got, *want)
	}
}

func TestLoad_NotFound(t *testing.T) {
	setHome(t)

	if _, err := Load(); err == nil {
		t.Error("expected error for missing config, got nil")
	}
}
