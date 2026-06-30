package config

import (
	"bytes"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
)

type YAMLStore struct {
	path string
}

// Compile-time guarantee that FileStore satisfies the Store port. If the port
// and this adapter ever drift, the build breaks here.
var _ Store = (*YAMLStore)(nil)

// NewFileStore wires a FileStore over an explicit config path.
func NewFileStore(path string) *YAMLStore {
	return &YAMLStore{path: path}
}

func DefaultStore() (*YAMLStore, error) {
	path, err := defaultPath()
	if err != nil {
		return nil, err
	}
	return NewFileStore(path), nil
}

func defaultPath() (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", fmt.Errorf("locate home directory: %w", err)
	}
	return filepath.Join(home, ".goph", "config.yaml"), nil
}

func (s *YAMLStore) Load() (*Config, error) {
	data, err := os.ReadFile(s.path)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil, fmt.Errorf("%w: %s", ErrConfigNotFound, s.path)
		}
		return nil, fmt.Errorf("read config %s: %w", s.path, err)
	}

	dec := yaml.NewDecoder(bytes.NewReader(data))
	dec.KnownFields(true)

	cfg := Default()
	if err := dec.Decode(cfg); err != nil && !errors.Is(err, io.EOF) {
		return nil, fmt.Errorf("parse config %s: %w", s.path, err)
	}

	return cfg, nil
}

func (s *YAMLStore) Save(c *Config) error {
	dir := filepath.Dir(s.path)
	if err := os.MkdirAll(dir, 0o700); err != nil {
		return fmt.Errorf("create config dir %s: %w", dir, err)
	}

	data, err := yaml.Marshal(c)
	if err != nil {
		return fmt.Errorf("encode config: %w", err)
	}

	if err := os.WriteFile(s.path, data, 0o600); err != nil {
		return fmt.Errorf("write config %s: %w", s.path, err)
	}

	return nil
}
