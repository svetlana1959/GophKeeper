package vault

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"

	_ "modernc.org/sqlite"
)

type Adapter struct {
	DB *sql.DB
}

func Open(path string) (*Adapter, error) {
	if path == "" {
		return nil, fmt.Errorf("vault: database path is required")
	}
	if path != ":memory:" {
		dir := filepath.Dir(path)
		if err := os.MkdirAll(dir, 0o700); err != nil {
			return nil, fmt.Errorf("vault: cannot create database directory %s: %w", dir, err)
		}
	}

	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("vault: failed to open sqlite database: %w", err)
	}
	db.SetMaxOpenConns(1)

	if err := db.Ping(); err != nil {
		db.Close()
		return nil, fmt.Errorf("vault: cannot connect to sqlite database: %w", err)
	}

	if err := enableForeignKeys(db); err != nil {
		db.Close()
		return nil, err
	}
	if err := migrate(db); err != nil {
		db.Close()
		return nil, err
	}

	return &Adapter{DB: db}, nil
}

func (a *Adapter) Close() error {
	if a == nil || a.DB == nil {
		return nil
	}
	return a.DB.Close()
}

func (a *Adapter) TrustedDeviceRepo() *TrustedDeviceRepo {
	return NewTrustedDeviceRepo(a.DB)
}

func (a *Adapter) LocalDeviceRepo() *LocalDeviceRepo {
	return NewLocalDeviceRepo(a.DB)
}

func (a *Adapter) SecretRepo() *SecretRepo {
	return NewSecretRepo(a.DB)
}

func (a *Adapter) SecretRecipientRepo() *SecretRecipientRepo {
	return NewSecretRecipientRepo(a.DB)
}

func enableForeignKeys(db *sql.DB) error {
	if _, err := db.Exec(`PRAGMA foreign_keys = ON`); err != nil {
		return fmt.Errorf("vault: failed to enable foreign keys: %w", err)
	}
	return nil
}

func migrate(db *sql.DB) error {
	schema := []string{
		`CREATE TABLE IF NOT EXISTS trusted_devices (
			id TEXT PRIMARY KEY,
			device_name TEXT NOT NULL,
			public_key TEXT NOT NULL,
			is_active INTEGER DEFAULT 1,
			updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
		);`,
		`CREATE TABLE IF NOT EXISTS local_device (
			device_id TEXT PRIMARY KEY,
			private_key_encrypted BLOB NOT NULL,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (device_id) REFERENCES trusted_devices(id) ON DELETE CASCADE
		);`,
		`CREATE TABLE IF NOT EXISTS secrets (
			id TEXT PRIMARY KEY,
			name TEXT NOT NULL UNIQUE,
			folder_id TEXT,
			encrypted_payload BLOB NOT NULL,
			nonce BLOB NOT NULL,
			version INTEGER DEFAULT 1,
			is_deleted INTEGER DEFAULT 0,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
		);`,
		`CREATE TABLE IF NOT EXISTS secret_recipients (
			secret_id TEXT NOT NULL,
			device_id TEXT NOT NULL,
			encrypted_dek BLOB NOT NULL,
			PRIMARY KEY (secret_id, device_id),
			FOREIGN KEY (secret_id) REFERENCES secrets(id) ON DELETE CASCADE,
			FOREIGN KEY (device_id) REFERENCES trusted_devices(id) ON DELETE CASCADE
		);`,
		`CREATE INDEX IF NOT EXISTS idx_recipients_device ON secret_recipients(device_id);`,
	}

	for _, stmt := range schema {
		if _, err := db.Exec(stmt); err != nil {
			return fmt.Errorf("vault: schema migration failed: %w", err)
		}
	}
	return nil
}
