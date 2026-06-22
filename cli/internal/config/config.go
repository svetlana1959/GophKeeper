package config

import (
    "bytes"
    "errors"
    "fmt"
    "os"
    "path/filepath"
    "runtime"
    "strings"

    "gopkg.in/yaml.v3"
)

var (
    ErrConfigNotFound = errors.New("config file not found")
    ErrMissingRemote  = errors.New("remote URL is required")
)

type Config struct {
    Remote        string `yaml:"remote"`
    SecretDB      string `yaml:"secret-db,omitempty"`
    DeviceName    string `yaml:"device-name,omitempty"`
    DefaultFolder string `yaml:"default-folder,omitempty"`
}

type Adapter struct {
    configDir  string
    configPath string
}

func NewAdapter() (*Adapter, error) {
    configDir, err := DefaultConfigDir()
    if err != nil {
        return nil, err
    }
    return NewAdapterWithDir(configDir), nil
}

func NewAdapterWithDir(configDir string) *Adapter {
    return &Adapter{
        configDir:  configDir,
        configPath: filepath.Join(configDir, "config.yaml"),
    }
}

func DefaultConfigDir() (string, error) {
    home, err := os.UserHomeDir()
    if err != nil {
        if runtime.GOOS == "windows" {
            home = os.Getenv("USERPROFILE")
        } else {
            home = os.Getenv("HOME")
        }
    }
    if home == "" {
        if err != nil {
            return "", fmt.Errorf("cannot determine home directory: %w", err)
        }
        return "", errors.New("cannot determine home directory")
    }
    return filepath.Join(home, ".goph"), nil
}

func DefaultConfigPath() (string, error) {
    configDir, err := DefaultConfigDir()
    if err != nil {
        return "", err
    }
    return filepath.Join(configDir, "config.yaml"), nil
}

func (a *Adapter) ConfigDir() string {
    return a.configDir
}

func (a *Adapter) ConfigPath() string {
    return a.configPath
}

func (a *Adapter) ensureConfigDir() error {
    return os.MkdirAll(a.configDir, 0o700)
}

func (a *Adapter) Read() (*Config, error) {
    if err := a.ensureConfigDir(); err != nil {
        return nil, fmt.Errorf("cannot create config directory %s: %w", a.configDir, err)
    }

    data, err := os.ReadFile(a.configPath)
    if err != nil {
        if errors.Is(err, os.ErrNotExist) {
            return nil, fmt.Errorf("%w: %s", ErrConfigNotFound, a.configPath)
        }
        return nil, fmt.Errorf("failed to read config file: %w", err)
    }

    cfg := &Config{}
    decoder := yaml.NewDecoder(bytes.NewReader(data))
    decoder.KnownFields(true)
    if err := decoder.Decode(cfg); err != nil {
        return nil, fmt.Errorf("failed to decode config.yaml: %w", err)
    }
    a.applyDefaults(cfg)
    return cfg, nil
}

func (a *Adapter) Write(cfg *Config) error {
    if err := a.ensureConfigDir(); err != nil {
        return fmt.Errorf("cannot create config directory %s: %w", a.configDir, err)
    }

    a.applyDefaults(cfg)
    data, err := yaml.Marshal(cfg)
    if err != nil {
        return fmt.Errorf("failed to marshal config: %w", err)
    }

    if err := os.WriteFile(a.configPath, data, 0o600); err != nil {
        return fmt.Errorf("failed to write config file: %w", err)
    }
    return nil
}

func (a *Adapter) applyDefaults(cfg *Config) {
    if cfg.SecretDB == "" {
        cfg.SecretDB = filepath.Join(a.configDir, "secrets.db")
    }
}

func (cfg *Config) Validate() error {
    if strings.TrimSpace(cfg.Remote) == "" {
        return ErrMissingRemote
    }
    if strings.TrimSpace(cfg.SecretDB) == "" {
        return errors.New("secret-db is required")
    }
    return nil
}
