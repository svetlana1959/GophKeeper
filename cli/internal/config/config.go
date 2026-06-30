package config

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

type Config struct {
	Remote        string `yaml:"remote"`         // backend URL used for push/pull
	SecretDB      string `yaml:"secret-db"`      // path to the local SQLite secret store
	DeviceName    string `yaml:"device-name"`    // human-readable device identity
	DefaultFolder string `yaml:"default-folder"` // folder new secrets land in by default
}

const DefaultSecretDB = "~/.goph/secrets.db"

func Default() *Config {
	return &Config{SecretDB: DefaultSecretDB}
}

func (c *Config) ResolveSecretDB() (string, error) {
	if c.SecretDB == "" {
		return "", errors.New("no secret database path configured")
	}
	return expandHome(c.SecretDB)
}

func expandHome(path string) (string, error) {
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

type Store interface {
	Load() (*Config, error)
	Save(c *Config) error
}

// ErrConfigNotFound is returned by a Store when no config exists yet, so
// callers can bootstrap one with Default instead of failing.
var ErrConfigNotFound = errors.New("config not found")
