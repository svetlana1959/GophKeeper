// Package config is the adapter for reading and writing the non-secret client
// configuration. The file lives at $HOME/.goph/config.yaml (or
// %USERPROFILE%\.goph\config.yaml on Windows) and is YAML, for example:
//
//	remote: https://example.com    # backend API URL used by push/pull
//	secret-db: ~/.goph/secrets.db  # path to the local SQLite secret store
//	device-name: laptop            # human-readable device identity
//	default-folder: personal       # folder new secrets land in by default
package config

import (
	"bytes"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	"gopkg.in/yaml.v3"
)

// Config holds the non-secret client settings persisted in config.yaml.
type Config struct {
	Remote        string `yaml:"remote"`         // backend URL used for push/pull
	SecretDB      string `yaml:"secret-db"`      // path to the local SQLite secret store
	DeviceName    string `yaml:"device-name"`    // human-readable device identity
	DefaultFolder string `yaml:"default-folder"` // folder new secrets land in by default
}

// DefaultSecretDB is the secret store path used when none is configured.
const DefaultSecretDB = "~/.goph/secrets.db"

func Default() *Config {
	return &Config{
		SecretDB: DefaultSecretDB,
	}
}

// ConfigPath returns the absolute path to the config file, e.g. ~/.goph/config.yaml.
func ConfigPath() (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", fmt.Errorf("could not get user home directory: %w", err)
	}
	return filepath.Join(home, ".goph", "config.yaml"), nil
}

// expandPath replaces a leading ~ (bare or ~/...) with the user home dir.
// The ~user form is not supported and is rejected rather than silently
// resolved to the wrong directory.
func expandPath(path string) (string, error) {
	if path != "~" && !strings.HasPrefix(path, "~/") {
		if strings.HasPrefix(path, "~") {
			return "", fmt.Errorf("unsupported ~user path expansion: %q", path)
		}
		return path, nil
	}
	home, err := os.UserHomeDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(home, strings.TrimPrefix(path, "~")), nil
}

// Load reads the config from the default path returned by ConfigPath,
// applying defaults for missing fields. It returns an error if the file is
// missing or malformed.
func Load() (*Config, error) {
	path, err := ConfigPath()
	if err != nil {
		return nil, err
	}
	return LoadFromFile(path)
}

// LoadFromFile reads and parses the config at path, applying defaults for
// missing fields. Unknown keys are rejected.
func LoadFromFile(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("config file not found: %w", err)
		}
		return nil, fmt.Errorf("error reading config file: %w", err)
	}

	// KnownFields(true) rejects unknown keys, so the set of accepted fields
	// stays defined solely by the Config struct tags.
	dec := yaml.NewDecoder(bytes.NewReader(data))
	dec.KnownFields(true)

	cfg := Default()
	if err := dec.Decode(cfg); err != nil && !errors.Is(err, io.EOF) {
		return nil, fmt.Errorf("error parsing YAML: %w", err)
	}

	return cfg, nil
}

// Save writes the config to the default path returned by ConfigPath.
func (c *Config) Save() error {
	path, err := ConfigPath()
	if err != nil {
		return err
	}
	return c.SaveToFile(path)
}

// SaveToFile writes the config to path, creating the parent directory with
// 0700 permissions and the file itself with 0600.
func (c *Config) SaveToFile(path string) error {
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0700); err != nil {
		return fmt.Errorf("could not create directory for config: %w", err)
	}

	data, err := yaml.Marshal(c)
	if err != nil {
		return fmt.Errorf("error serializing config to YAML: %w", err)
	}

	if err := os.WriteFile(path, data, 0600); err != nil {
		return fmt.Errorf("error writing config file: %w", err)
	}

	return nil
}

// ValidateForSync reports whether the config has the fields required to sync
// with the remote backend.
func (c *Config) ValidateForSync() error {
	if c.Remote == "" {
		return errors.New("for synchronization you must specify a remote URL")
	}
	return nil
}

func (c *Config) ResolveSecretDB() (string, error) {
	if c.SecretDB == "" {
		return "", errors.New("no path to the secret database is configured")
	}
	return expandPath(c.SecretDB)
}
