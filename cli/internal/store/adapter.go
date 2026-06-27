// Package store is the local encrypted secret store. It is the only package in
// the project that contains SQL. It stores ciphertext / opaque blobs only and
// never sees plaintext secrets.
package store

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	_ "modernc.org/sqlite" // pure-Go driver, registered as "sqlite"
)

// Adapter owns the DB lifecycle.
type Adapter struct {
	db   *sql.DB
	path string
}

// Open opens (creating if missing) the SQLite database at dbPath, creating its
// parent directory (e.g. ~/.goph) with 0700, running migrations, and enforcing
// 0600 on the DB file. For in-memory DBs the filesystem steps are skipped.
func Open(ctx context.Context, dbPath string) (*Adapter, error) {
	if dbPath == "" {
		return nil, fmt.Errorf("store: db path is required")
	}

	if !isMemory(dbPath) {
		if dir := filepath.Dir(dbPath); dir != "" && dir != "." {
			if err := os.MkdirAll(dir, 0o700); err != nil {
				return nil, fmt.Errorf("store: create dir %q: %w", dir, err)
			}
		}
	}

	dsn := fmt.Sprintf(
		"file:%s?_pragma=foreign_keys(1)&_pragma=journal_mode(WAL)&_pragma=busy_timeout(5000)",
		dbPath,
	)
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("store: open: %w", err)
	}
	// Single-writer local store: one connection avoids SQLITE_BUSY and keeps
	// a ":memory:" DB stable across calls (each pooled conn would otherwise be
	// a separate in-memory database).
	db.SetMaxOpenConns(1)

	if err := db.PingContext(ctx); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("store: ping: %w", err)
	}

	a := &Adapter{db: db, path: dbPath}
	if err := a.migrate(ctx); err != nil {
		_ = db.Close()
		return nil, err
	}

	if !isMemory(dbPath) {
		if err := os.Chmod(dbPath, 0o600); err != nil {
			_ = db.Close()
			return nil, fmt.Errorf("store: chmod 0600: %w", err)
		}
	}
	return a, nil
}

// Close releases the database handle.
func (a *Adapter) Close() error {
	if a == nil || a.db == nil {
		return nil
	}
	return a.db.Close()
}

// DB exposes the handle for advanced callers (e.g. transactions). Optional.
func (a *Adapter) DB() *sql.DB { return a.db }

// Repository constructors (the CLI uses these).
func (a *Adapter) Devices() *DeviceRepository          { return &DeviceRepository{db: a.db} }
func (a *Adapter) LocalDevice() *LocalDeviceRepository { return &LocalDeviceRepository{db: a.db} }
func (a *Adapter) Secrets() *SecretRepository          { return &SecretRepository{db: a.db} }
func (a *Adapter) Recipients() *RecipientRepository    { return &RecipientRepository{db: a.db} }

func (a *Adapter) migrate(ctx context.Context) error {
	for _, stmt := range strings.Split(schema, ";") {
		s := strings.TrimSpace(stmt)
		if s == "" {
			continue
		}
		if _, err := a.db.ExecContext(ctx, s); err != nil {
			return fmt.Errorf("store: migrate %q: %w", firstLine(s), err)
		}
	}
	return nil
}

// --- shared helpers ------------------------------------------------------

type rowScanner interface {
	Scan(dest ...any) error
}

func isMemory(path string) bool {
	return path == ":memory:" ||
		strings.Contains(path, ":memory:") ||
		strings.Contains(path, "mode=memory")
}

func firstLine(s string) string {
	if i := strings.IndexByte(s, '\n'); i >= 0 {
		return s[:i]
	}
	return s
}

func boolToInt(b bool) int {
	if b {
		return 1
	}
	return 0
}

func nowUTC() time.Time { return time.Now().UTC() }

func fmtTime(t time.Time) string { return t.UTC().Format(time.RFC3339Nano) }

// parseTime tolerates both our RFC3339 writes and SQLite's CURRENT_TIMESTAMP
// default ("2006-01-02 15:04:05").
func parseTime(s string) (time.Time, error) {
	for _, layout := range []string{time.RFC3339Nano, time.RFC3339, "2006-01-02 15:04:05"} {
		if t, err := time.Parse(layout, s); err == nil {
			return t.UTC(), nil
		}
	}
	return time.Time{}, fmt.Errorf("store: cannot parse time %q", s)
}

func checkAffected(res sql.Result) error {
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("store: rows affected: %w", err)
	}
	if n == 0 {
		return ErrNotFound
	}
	return nil
}

func nullable(s string) any {
	if s == "" {
		return nil
	}
	return s
}
