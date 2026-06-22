/* Config example
remote: https://example.com          # backend API URL (used by push/pull)
secret-db: ~/.goph/secrets.db        # path to the local SQLite secret store (#33)
device-name: laptop          		 # human-readable device identity
default-folder: personal   			 # folder new secrets land in by default (categorization)
*/

// Package config provides an adapter for reading and writing client configuration.
// The config is stored in YAML at $HOME/.goph/config.yaml (or %USERPROFILE%\.goph\config.yaml on Windows).
package config

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"gopkg.in/yaml.v3"
)

// Config — structure reflecting the content of the configuration file.
type Config struct {
	Remote        string `yaml:"remote"`          // Backend URL (used for push/pull)
	SecretDB      string `yaml:"secret-db"`       // Path to the local SQLite secret store
	DeviceName    string `yaml:"device-name"`      // Human-readable device identity
	DefaultFolder string `yaml:"default-folder"`   // Default folder for new secrets
}

// Default secret DB value
const DefaultSecretDB = "~/.goph/secrets.db"

// Returns path to the config file, e.g. ~/.goph/config.yaml
func ConfigPath() (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", fmt.Errorf("Could not get user home directory: %w", err)
	}
	return filepath.Join(home, ".goph", "config.yaml"), nil
}

// expandPath replaces ~ with the user home dir
func expandPath(path string) (string, error) {
	if strings.HasPrefix(path, "~") {
		home, err := os.UserHomeDir()
		if err != nil {
			return "", err
		}
		return filepath.Join(home, strings.TrimPrefix(path, "~")), nil
	}
	return path, nil
}

// Load loads config from default path defined by ConfigPath()
// Applies default values if fields are missing
// Returns an error if the file is not found or has an invalid format
func Load() (*Config, error) {
	path, err := ConfigPath()
	if err != nil {
		return nil, err
	}
	return LoadFromFile(path)
}

// LoadFromFile reads config from a file
func LoadFromFile(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("Config file not found: %w", err)
		}
		return nil, fmt.Errorf("Error reading config file: %w", err)
	}

	var cfg Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("Error parsing YAML: %w", err)
	}

	// Setting default values for missing field SecretDB
	if cfg.SecretDB == "" {
		cfg.SecretDB = DefaultSecretDB
	}

	return &cfg, nil
}

// Save writes the config to the default path defined by ConfigPath()
// Creates the .goph directory with 0700 permissions if it doesn't exist
// The file is saved with 0600 permissions
func (c *Config) Save() error {
	path, err := ConfigPath()
	if err != nil {
		return err
	}
	return c.SaveToFile(path)
}

// SaveToFile writes the config to a specified file path
// Creates the parent directory with 0700 permissions if it doesn't exist
func (c *Config) SaveToFile(path string) error {
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0700); err != nil {
		return fmt.Errorf("Could not create directory for config: %w", err)
	}

	data, err := yaml.Marshal(c)
	if err != nil {
		return fmt.Errorf("Error serializing config to YAML: %w", err)
	}

	if err := os.WriteFile(path, data, 0600); err != nil {
		return fmt.Errorf("Error writing config file: %w", err)
	}

	return nil
}

// ValidateForSync checks that the config has the necessary fields for synchronization
func (c *Config) ValidateForSync() error {
	if c.Remote == "" {
		return errors.New("For synchronization you must specify a remote URL")
	}
	return nil
}

// ResolveSecretDB returns the absolute path to the secret database, expanding ~ if necessary.
func (c *Config) ResolveSecretDB() (string, error) {
	if c.SecretDB == "" {
		return "", errors.New("For synchronization you must specify a path to the secret database")
	}
	return expandPath(c.SecretDB)
}