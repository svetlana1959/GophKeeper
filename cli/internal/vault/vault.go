package vault

import (
	"database/sql"
	_ "embed"
	"fmt"
	"os"
	"path/filepath"

	"github.com/svetlana1959/GophKeeper/cli/internal/device"
	"github.com/svetlana1959/GophKeeper/cli/internal/secret"
	"github.com/svetlana1959/GophKeeper/cli/internal/syncstate"

	_ "modernc.org/sqlite"
)

//go:embed schema.sql
var schema string

// DB is the SQLite-backed adapter. It owns the connection lifecycle and
// hands out the domain repositories; no business logic lives here.
type DB struct {
	sql *sql.DB
}

// Open ensures the parent directory (0700) and database file (0600) exist, opens
// the SQLite database with foreign keys enabled, and applies the schema. It is
// safe to call on an existing database — the schema is created idempotently.
func Open(path string) (*DB, error) {
	if dir := filepath.Dir(path); dir != "" && dir != "." {
		if err := os.MkdirAll(dir, 0o700); err != nil {
			return nil, fmt.Errorf("vault: create dir %s: %w", dir, err)
		}
	}

	// Create the file ourselves so it is never world-readable, even briefly.
	f, err := os.OpenFile(path, os.O_CREATE, 0o600)
	if err != nil {
		return nil, fmt.Errorf("vault: create db file %s: %w", path, err)
	}
	f.Close()
	if err := os.Chmod(path, 0o600); err != nil {
		return nil, fmt.Errorf("vault: secure db file %s: %w", path, err)
	}

	// _pragma options are applied to every pooled connection. foreign_keys must
	// be on per-connection or ON DELETE CASCADE silently does nothing.
	dsn := "file:" + path + "?_pragma=foreign_keys(1)&_pragma=busy_timeout(5000)"
	sqlDB, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("vault: open %s: %w", path, err)
	}
	// SQLite is single-writer; one connection avoids "database is locked".
	sqlDB.SetMaxOpenConns(1)

	if _, err := sqlDB.Exec(schema); err != nil {
		sqlDB.Close()
		return nil, fmt.Errorf("vault: apply schema: %w", err)
	}

	return &DB{sql: sqlDB}, nil
}

// Close releases the database connection.
func (db *DB) Close() error { return db.sql.Close() }

// Secrets returns the secrets repository.
func (db *DB) Secrets() secret.Repository { return &secretRepo{db: db.sql} }

// Devices returns the trusted-devices repository.
func (db *DB) Devices() device.Repository { return &deviceRepo{db: db.sql} }

// Local returns the local-device repository.
func (db *DB) Local() device.LocalRepository { return &localRepo{db: db.sql} }

// Sync returns the synchronization-state repository.
func (db *DB) Sync() syncstate.Repository { return &syncRepo{db: db.sql} }
