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
	t.Setenv("USERPROFILE", home) // for Windows

	path, err := ConfigPath()
	if err != nil {
		t.Fatalf("ConfigPath returned error: %v", err)
	}
	expected := filepath.Join(home, ".goph", "config.yaml")
	if path != expected {
		t.Errorf("expected path %q, got %q", expected, path)
	}
}

func TestLoadFromFile_NotFound(t *testing.T) {
	tmpDir := t.TempDir()
	path := filepath.Join(tmpDir, "notexist.yaml")

	_, err := LoadFromFile(path)
	if err == nil {
		t.Error("expected error for non-existent file, but got nil")
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
		t.Error("expected parsing error, but got nil")
	}
}

func TestLoadFromFile_Valid(t *testing.T) {
	tmpDir := t.TempDir()
	path := filepath.Join(tmpDir, "config.yaml")
	content := `
remote: https://example.com
device-name: laptop
default-folder: work
# secret-db is omitted – the default should be applied
`
	if err := os.WriteFile(path, []byte(content), 0600); err != nil {
		t.Fatal(err)
	}

	cfg, err := LoadFromFile(path)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if cfg.Remote != "https://example.com" {
		t.Errorf("remote = %q, awaited = %q", cfg.Remote, "https://example.com")
	}
	if cfg.DeviceName != "laptop" {
		t.Errorf("deviceName = %q, awaited = %q", cfg.DeviceName, "laptop")
	}
	if cfg.DefaultFolder != "work" {
		t.Errorf("defaultFolder = %q, awaited = %q", cfg.DefaultFolder, "work")
	}
	if cfg.SecretDB != DefaultSecretDB {
		t.Errorf("secretDB = %q, awaited default value = %q", cfg.SecretDB, DefaultSecretDB)
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
		t.Error("expected error for unknown field, but got nil")
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
		t.Fatalf("saveToFile returned error: %v", err)
	}

	info, err := os.Stat(path)
	if err != nil {
		t.Fatalf("file not created: %v", err)
	}

	// Permission checks only work reliably on Unix-like systems
	if runtime.GOOS != "windows" {
		if info.Mode().Perm() != 0600 {
			t.Errorf("file permissions: %v (expected 0600)", info.Mode().Perm())
		}
	}

	dirInfo, err := os.Stat(filepath.Dir(path))
	if err != nil {
		t.Fatalf("directory not created: %v", err)
	}

	if runtime.GOOS != "windows" {
		if dirInfo.Mode().Perm() != 0700 {
			t.Errorf("directory permissions: %v (expected 0700)", dirInfo.Mode().Perm())
		}
	}

	loaded, err := LoadFromFile(path)
	if err != nil {
		t.Fatalf("could not load saved config: %v", err)
	}
	if loaded.Remote != cfg.Remote || loaded.DeviceName != cfg.DeviceName {
		t.Errorf("loaded config does not match saved config")
	}
}

func TestValidateForSync(t *testing.T) {
	cfg := &Config{Remote: ""}
	if err := cfg.ValidateForSync(); err == nil {
		t.Error("expected error for empty remote URL")
	}

	cfg.Remote = "https://valid.com"
	if err := cfg.ValidateForSync(); err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestResolveSecretDB(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)
	t.Setenv("USERPROFILE", home)

	cfg := &Config{SecretDB: "~/secrets.db"}
	resolved, err := cfg.ResolveSecretDB()
	if err != nil {
		t.Fatalf("resolveSecretDB returned error: %v", err)
	}
	expected := filepath.Join(home, "secrets.db")
	if resolved != expected {
		t.Errorf("resolved path %q, expected %q", resolved, expected)
	}

	absPath := "/absolute/path.db"
	cfg.SecretDB = absPath
	resolved, err = cfg.ResolveSecretDB()
	if err != nil {
		t.Fatalf("resolveSecretDB returned error: %v", err)
	}
	if resolved != absPath {
		t.Errorf("absolute path was modified: %q instead of %q", resolved, absPath)
	}
}

func TestSave_Load_Default(t *testing.T) {
	// Use a temporary home directory for this test
	home := t.TempDir()
	t.Setenv("HOME", home)
	t.Setenv("USERPROFILE", home)

	// Create original config
	originalCfg := &Config{
		Remote:        "https://api.example.com",
		SecretDB:      "~/goph/secrets.db",
		DeviceName:    "test-machine",
		DefaultFolder: "personal",
	}

	// Save to default path
	if err := originalCfg.Save(); err != nil {
		t.Fatalf("save returned error: %v", err)
	}

	// Load from default path
	loadedCfg, err := Load()
	if err != nil {
		t.Fatalf("load returned error: %v", err)
	}

	// Verify loaded config matches original
	if loadedCfg.Remote != originalCfg.Remote {
		t.Errorf("remote mismatch: got %q, expected %q", loadedCfg.Remote, originalCfg.Remote)
	}
	if loadedCfg.DeviceName != originalCfg.DeviceName {
		t.Errorf("deviceName mismatch: got %q, expected %q", loadedCfg.DeviceName, originalCfg.DeviceName)
	}
	if loadedCfg.DefaultFolder != originalCfg.DefaultFolder {
		t.Errorf("defaultFolder mismatch: got %q, expected %q", loadedCfg.DefaultFolder, originalCfg.DefaultFolder)
	}
	if loadedCfg.SecretDB != originalCfg.SecretDB {
		t.Errorf("secretDB mismatch: got %q, expected %q", loadedCfg.SecretDB, originalCfg.SecretDB)
	}
}

func TestLoadFromFile_Empty(t *testing.T) {
	tmpDir := t.TempDir()
	path := filepath.Join(tmpDir, "config.yaml")
	if err := os.WriteFile(path, []byte(""), 0600); err != nil {
		t.Fatal(err)
	}

	cfg, err := LoadFromFile(path)
	if err != nil {
		t.Fatalf("empty config should load with defaults, got error: %v", err)
	}
	if cfg.SecretDB != DefaultSecretDB {
		t.Errorf("secretDB = %q, expected default %q", cfg.SecretDB, DefaultSecretDB)
	}
}

func TestResolveSecretDB_RejectsUserPath(t *testing.T) {
	cfg := &Config{SecretDB: "~bob/secrets.db"}
	if _, err := cfg.ResolveSecretDB(); err == nil {
		t.Error("expected error for ~user path, but got nil")
	}
}

func TestLoad_NotFound(t *testing.T) {
	// Use a temporary home directory that has no config file
	home := t.TempDir()
	t.Setenv("HOME", home)
	t.Setenv("USERPROFILE", home)

	// Try to load from non-existent default path
	_, err := Load()
	if err == nil {
		t.Error("expected error for missing config file, but got nil")
	}
}
