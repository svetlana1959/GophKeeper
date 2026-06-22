package config

import (
    "os"
    "path/filepath"
    "runtime"
    "strings"
    "testing"
)

func TestReadMissingConfigCreatesDirectory(t *testing.T) {
    tempDir := t.TempDir()
    adapter := NewAdapterWithDir(tempDir)

    _, err := adapter.Read()
    if err == nil {
        t.Fatal("expected missing config error")
    }
    if !strings.Contains(err.Error(), ErrConfigNotFound.Error()) {
        t.Fatalf("expected ErrConfigNotFound, got %v", err)
    }

    info, err := os.Stat(adapter.ConfigDir())
    if err != nil {
        t.Fatalf("expected config dir to exist: %v", err)
    }
    if !info.IsDir() {
        t.Fatal("config dir path is not a directory")
    }
    if runtime.GOOS != "windows" && info.Mode().Perm() != 0o700 {
        t.Fatalf("expected config dir mode 0700, got %o", info.Mode().Perm())
    }
}

func TestWriteReadConfigWithDefaults(t *testing.T) {
    tempDir := t.TempDir()
    adapter := NewAdapterWithDir(tempDir)

    original := &Config{
        Remote:        "https://example.com",
        DeviceName:    "laptop",
        DefaultFolder: "personal",
    }

    if err := adapter.Write(original); err != nil {
        t.Fatal(err)
    }

    info, err := os.Stat(adapter.ConfigPath())
    if err != nil {
        t.Fatalf("expected config file to exist: %v", err)
    }
    if runtime.GOOS != "windows" && info.Mode().Perm() != 0o600 {
        t.Fatalf("expected config file mode 0600, got %o", info.Mode().Perm())
    }

    readConfig, err := adapter.Read()
    if err != nil {
        t.Fatal(err)
    }
    if readConfig.Remote != original.Remote {
        t.Fatalf("remote mismatch: got %q, want %q", readConfig.Remote, original.Remote)
    }
    if readConfig.DeviceName != original.DeviceName {
        t.Fatalf("device-name mismatch: got %q, want %q", readConfig.DeviceName, original.DeviceName)
    }
    if readConfig.DefaultFolder != original.DefaultFolder {
        t.Fatalf("default-folder mismatch: got %q, want %q", readConfig.DefaultFolder, original.DefaultFolder)
    }
    expectedSecretDB := filepath.Join(adapter.ConfigDir(), "secrets.db")
    if readConfig.SecretDB != expectedSecretDB {
        t.Fatalf("secret-db mismatch: got %q, want %q", readConfig.SecretDB, expectedSecretDB)
    }
}

func TestReadMalformedConfig(t *testing.T) {
    tempDir := t.TempDir()
    adapter := NewAdapterWithDir(tempDir)

    if err := os.WriteFile(adapter.ConfigPath(), []byte("remote: https://example.com\nsecret-db: [unclosed"), 0o600); err != nil {
        t.Fatal(err)
    }

    _, err := adapter.Read()
    if err == nil {
        t.Fatal("expected malformed config error")
    }
    if !strings.Contains(err.Error(), "failed to decode config.yaml") {
        t.Fatalf("expected decode error, got %v", err)
    }
}

func TestConfigValidate(t *testing.T) {
    cfg := &Config{
        SecretDB: "/tmp/secrets.db",
    }
    if err := cfg.Validate(); err == nil {
        t.Fatal("expected validation error for missing remote")
    }
    if err := cfg.Validate(); !strings.Contains(err.Error(), ErrMissingRemote.Error()) {
        t.Fatalf("expected ErrMissingRemote, got %v", err)
    }

    cfg.Remote = "https://example.com"
    if err := cfg.Validate(); err != nil {
        t.Fatal(err)
    }
}
