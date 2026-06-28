// Package store is the local encrypted secret store. It is the only package in
// the project that contains SQL. It stores ciphertext / opaque blobs only and
// never sees plaintext secrets.
package store

import (
	"context"
	"crypto/aes"
	"crypto/cipher"
	"crypto/pbkdf2"
	"crypto/rand"
	"crypto/sha256"
	"database/sql"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"time"

	_ "modernc.org/sqlite" // pure-Go driver, registered as "sqlite"
)

// Adapter owns the DB lifecycle.
type Adapter struct {
	db     *sql.DB
	path   string
	config Config
}
type Config struct {
	Path     string // Database path or ":memory:" for in-memory
	Password string // Encryption password (empty = no encryption)
}

// Open opens (creating if missing) the SQLite database at dbPath, creating its
// parent directory (e.g. ~/.goph) with 0700, running migrations, and enforcing
// 0600 on the DB file. For in-memory DBs the filesystem steps are skipped.

func Open(ctx context.Context, dbPath string) (*Adapter, error) {
	return OpenWithConfig(ctx, Config{
		Path:     dbPath,
		Password: os.Getenv("DB_ENCRYPTION_PASSWORD"), // Get password from env
	})
}

func OpenWithConfig(ctx context.Context, cfg Config) (*Adapter, error) {
	if cfg.Path == "" {
		return nil, fmt.Errorf("store: db path is required")
	}

	// Handle in-memory database explicitly (tests only)
	if cfg.Path == ":memory:" {
		dsn := "file::memory:?_pragma=foreign_keys(1)&_pragma=journal_mode(WAL)&_pragma=busy_timeout(5000)"
		db, err := sql.Open("sqlite", dsn)
		if err != nil {
			return nil, fmt.Errorf("store: open memory db: %w", err)
		}
		db.SetMaxOpenConns(1)

		if err := db.PingContext(ctx); err != nil {
			_ = db.Close()
			return nil, fmt.Errorf("store: ping memory db: %w", err)
		}

		a := &Adapter{db: db, path: cfg.Path, config: cfg}
		if err := a.migrate(ctx); err != nil {
			_ = db.Close()
			return nil, err
		}
		return a, nil
	}

	// File-based database
	// Create directory if it doesn't exist
	if dir := filepath.Dir(cfg.Path); dir != "" && dir != "." {
		if err := os.MkdirAll(dir, 0o700); err != nil {
			return nil, fmt.Errorf("store: create dir %q: %w", dir, err)
		}
	}

	dsn := fmt.Sprintf(
		"file:%s?_pragma=foreign_keys(1)&_pragma=journal_mode(WAL)&_pragma=busy_timeout(5000)",
		cfg.Path,
	)

	// If password is provided, we use application-level encryption
	// SQLite itself doesn't have built-in encryption, so we handle it in the application

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

	a := &Adapter{db: db, path: cfg.Path, config: cfg}
	if err := a.migrate(ctx); err != nil {
		_ = db.Close()
		return nil, err
	}

	// Set restrictive permissions on the database file
	if err := os.Chmod(cfg.Path, 0o600); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("store: chmod 0600: %w", err)
	}

	return a, nil
}

// encryptData encrypts data using AES-GCM with a password-derived key
func encryptData(data []byte, password string) ([]byte, error) {
	if password == "" {
		return data, nil // No encryption
	}

	// Derive a key from the password using PBKDF2
	salt := []byte("GophKeeperStaticSalt2026") // In production, use random salt stored separately
	key, err := pbkdf2.Key(sha256.New, string([]byte(password)), salt, 4096, 32)
	if err != nil {
		return nil, fmt.Errorf("derive key: %w", err)
	}
	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, fmt.Errorf("create cipher: %w", err)
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, fmt.Errorf("create GCM: %w", err)
	}

	// Generate a random nonce
	nonce := make([]byte, gcm.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return nil, fmt.Errorf("generate nonce: %w", err)
	}

	// Encrypt and seal (nonce + encrypted data)
	encrypted := gcm.Seal(nonce, nonce, data, nil)
	return encrypted, nil
}

// decryptData decrypts data using AES-GCM with a password-derived key
func decryptData(encrypted []byte, password string) ([]byte, error) {
	if password == "" {
		return encrypted, nil // No encryption
	}

	// Derive the key from the password
	salt := []byte("GophKeeperStaticSalt2026")
	key, err := pbkdf2.Key(sha256.New, string([]byte(password)), salt, 4096, 32)
	if err != nil {
		return nil, fmt.Errorf("derive key: %w", err)
	}
	// Create AES-GCM cipher
	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, fmt.Errorf("create cipher: %w", err)
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, fmt.Errorf("create GCM: %w", err)
	}

	nonceSize := gcm.NonceSize()
	if len(encrypted) < nonceSize {
		return nil, fmt.Errorf("ciphertext too short")
	}

	// Extract nonce and ciphertext
	nonce, ciphertext := encrypted[:nonceSize], encrypted[nonceSize:]

	// Decrypt
	decrypted, err := gcm.Open(nil, nonce, ciphertext, nil)
	if err != nil {
		return nil, fmt.Errorf("decrypt: %w", err)
	}

	return decrypted, nil
}

// SaveSecure encrypts and saves data securely
func (a *Adapter) SaveSecure(table, column string, id string, data []byte) error {
	// Encrypt the data if password is configured
	var err error
	if a.config.Password != "" {
		data, err = encryptData(data, a.config.Password)
		if err != nil {
			return fmt.Errorf("encrypt data: %w", err)
		}
	}

	// Save to database
	query := fmt.Sprintf("UPDATE %s SET %s = ? WHERE id = ?", table, column)
	_, err = a.db.Exec(query, data, id)
	return err
}

// LoadSecure decrypts and loads data securely
func (a *Adapter) LoadSecure(table, column string, id string) ([]byte, error) {
	var encryptedData []byte
	query := fmt.Sprintf("SELECT %s FROM %s WHERE id = ?", column, table)
	err := a.db.QueryRow(query, id).Scan(&encryptedData)
	if err != nil {
		return nil, err
	}

	// Decrypt the data if password is configured
	if a.config.Password != "" {
		return decryptData(encryptedData, a.config.Password)
	}

	return encryptedData, nil
}

// Close releases the database handle.
func (a *Adapter) Close() error {
	if a == nil || a.db == nil {
		return nil
	}
	return a.db.Close()
}

// Repository constructors (the CLI uses these).

func (a *Adapter) Devices() *DeviceRepository          { return &DeviceRepository{db: a.db} }
func (a *Adapter) LocalDevice() *LocalDeviceRepository { return &LocalDeviceRepository{db: a.db} }
func (a *Adapter) Secrets() *SecretRepository          { return &SecretRepository{db: a.db} }
func (a *Adapter) Recipients() *RecipientRepository    { return &RecipientRepository{db: a.db} }

func (a *Adapter) migrate(ctx context.Context) error {
	// Execute the entire schema as a single string.
	// SQLite's Exec API correctly handles multiple statements separated by semicolons,
	// even when semicolons appear inside string literals or statement bodies.
	if _, err := a.db.ExecContext(ctx, schema); err != nil {
		return fmt.Errorf("store: migrate schema: %w", err)
	}
	return nil
}

// --- shared helpers ------------------------------------------------------

type rowScanner interface {
	Scan(dest ...any) error
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
