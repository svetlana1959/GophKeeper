package config

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

func TestConfigPath(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)
	t.Setenv("USERPROFILE", home) // для Windows

	path, err := ConfigPath()
	if err != nil {
		t.Fatalf("ConfigPath returned error: %v", err)
	}
	expected := filepath.Join(home, ".goph", "config.yaml")
	if path != expected {
		t.Errorf("Expected path %q, got %q", expected, path)
	}
}

func TestLoadFromFile_NotFound(t *testing.T) {
	tmpDir := t.TempDir()
	path := filepath.Join(tmpDir, "notexist.yaml")

	_, err := LoadFromFile(path)
	if err == nil {
		t.Error("Expected error for non-existent file, but got nil")
	}
}

func TestLoadFromFile_Malformed(t *testing.T) {
	tmpDir := t.TempDir()
	path := filepath.Join(tmpDir, "config.yaml")
	if err := os.WriteFile(path, []byte("this is not yaml: [}"), 0600); err != nil {
		t.Fatal(err)
	}

	_, err := LoadFromFile(path)
	if err == nil {
		t.Error("Expected parsing error, but got nil")
	}
}

func TestLoadFromFile_Valid(t *testing.T) {
	tmpDir := t.TempDir()
	path := filepath.Join(tmpDir, "config.yaml")
	content := `
remote: https://example.com
device-name: laptop
default-folder: work
# secret-db отсутствует – должен подставиться дефолт
`
	if err := os.WriteFile(path, []byte(content), 0600); err != nil {
		t.Fatal(err)
	}

	cfg, err := LoadFromFile(path)
	if err != nil {
		t.Fatalf("Unexpected error: %v", err)
	}

	if cfg.Remote != "https://example.com" {
		t.Errorf("Remote = %q, awaited = %q", cfg.Remote, "https://example.com")
	}
	if cfg.DeviceName != "laptop" {
		t.Errorf("DeviceName = %q, awaited = %q", cfg.DeviceName, "laptop")
	}
	if cfg.DefaultFolder != "work" {
		t.Errorf("DefaultFolder = %q, awaited = %q", cfg.DefaultFolder, "work")
	}
	if cfg.SecretDB != DefaultSecretDB {
		t.Errorf("SecretDB = %q, awaited default value = %q", cfg.SecretDB, DefaultSecretDB)
	}
}

func TestLoadFromFile_UnknownField(t *testing.T) {
	tmpDir := t.TempDir()
	path := filepath.Join(tmpDir, "config.yaml")
	content := `
remote: https://example.com
device-name: laptop
typo-field: should-fail
`
	if err := os.WriteFile(path, []byte(content), 0600); err != nil {
		t.Fatal(err)
	}

	_, err := LoadFromFile(path)
	if err == nil {
		t.Error("Expected error for unknown field, but got nil")
	}
}

func TestSaveToFile(t *testing.T) {
	tmpDir := t.TempDir()
	path := filepath.Join(tmpDir, ".goph", "config.yaml")

	cfg := &Config{
		Remote:        "https://test.com",
		SecretDB:      "~/my.db",
		DeviceName:    "test-device",
		DefaultFolder: "test",
	}

	if err := cfg.SaveToFile(path); err != nil {
		t.Fatalf("SaveToFile returned error: %v", err)
	}

	info, err := os.Stat(path)
	if err != nil {
		t.Fatalf("File not created: %v", err)
	}

	// Permission checks only work reliably on Unix-like systems
	if runtime.GOOS != "windows" {
		if info.Mode().Perm() != 0600 {
			t.Errorf("File permissions: %v (expected 0600)", info.Mode().Perm())
		}
	}

	dirInfo, err := os.Stat(filepath.Dir(path))
	if err != nil {
		t.Fatalf("Directory not created: %v", err)
	}

	if runtime.GOOS != "windows" {
		if dirInfo.Mode().Perm() != 0700 {
			t.Errorf("Directory permissions: %v (expected 0700)", dirInfo.Mode().Perm())
		}
	}

	loaded, err := LoadFromFile(path)
	if err != nil {
		t.Fatalf("Could not load saved config: %v", err)
	}
	if loaded.Remote != cfg.Remote || loaded.DeviceName != cfg.DeviceName {
		t.Errorf("Loaded config does not match saved config")
	}
}

func TestValidateForSync(t *testing.T) {
	cfg := &Config{Remote: ""}
	if err := cfg.ValidateForSync(); err == nil {
		t.Error("Expected error for empty remote URL")
	}

	cfg.Remote = "https://valid.com"
	if err := cfg.ValidateForSync(); err != nil {
		t.Errorf("Unexpected error: %v", err)
	}
}

func TestResolveSecretDB(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)
	t.Setenv("USERPROFILE", home)

	cfg := &Config{SecretDB: "~/secrets.db"}
	resolved, err := cfg.ResolveSecretDB()
	if err != nil {
		t.Fatalf("ResolveSecretDB returned error: %v", err)
	}
	expected := filepath.Join(home, "secrets.db")
	if resolved != expected {
		t.Errorf("Resolved path %q, expected %q", resolved, expected)
	}

	absPath := "/absolute/path.db"
	cfg.SecretDB = absPath
	resolved, err = cfg.ResolveSecretDB()
	if err != nil {
		t.Fatalf("ResolveSecretDB returned error: %v", err)
	}
	if resolved != absPath {
		t.Errorf("Absolute path was modified: %q instead of %q", resolved, absPath)
	}
}
