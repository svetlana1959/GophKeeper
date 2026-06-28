package store

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
)

// SecretRepository: create / get / list / update / soft-delete.
type SecretRepository struct {
	db *sql.DB
}

// Create inserts a new secret. Returns ErrConflict if the id already exists.
func (r *SecretRepository) Create(ctx context.Context, s Secret) error {
	if s.ID == "" {
		return errors.New("store: secret id is required")
	}
	if len(s.EncryptedPayload) == 0 || len(s.Nonce) == 0 {
		return errors.New("store: encrypted payload and nonce are required")
	}
	if s.Version == 0 {
		s.Version = 1
	}
	now := nowUTC()
	if s.CreatedAt.IsZero() {
		s.CreatedAt = now
	}
	if s.UpdatedAt.IsZero() {
		s.UpdatedAt = now
	}
	const q = `
INSERT INTO secrets
    (id, folder_id, encrypted_payload, nonce, version, is_deleted, created_at, updated_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?);`
	_, err := r.db.ExecContext(ctx, q,
		s.ID, nullable(s.FolderID), s.EncryptedPayload, s.Nonce,
		s.Version, boolToInt(s.IsDeleted), fmtTime(s.CreatedAt), fmtTime(s.UpdatedAt))
	if err != nil {
		if isUniqueViolation(err) {
			return ErrConflict
		}
		return fmt.Errorf("store: create secret: %w", err)
	}
	return nil
}

// Get returns a secret by id (including tombstoned ones), or ErrNotFound.
func (r *SecretRepository) Get(ctx context.Context, id string) (Secret, error) {
	const q = `SELECT id, folder_id, encrypted_payload, nonce, version,
	                  is_deleted, created_at, updated_at
	           FROM secrets WHERE id = ?;`
	return scanSecret(r.db.QueryRowContext(ctx, q, id))
}

// List returns all non-deleted secrets ordered by creation time.
func (r *SecretRepository) List(ctx context.Context) ([]Secret, error) {
	const q = `SELECT id, folder_id, encrypted_payload, nonce, version,
	                  is_deleted, created_at, updated_at
	           FROM secrets WHERE is_deleted = 0 ORDER BY created_at;`
	rows, err := r.db.QueryContext(ctx, q)
	if err != nil {
		return nil, fmt.Errorf("store: list secrets: %w", err)
	}
	defer rows.Close()

	var out []Secret
	for rows.Next() {
		s, err := scanSecret(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, s)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("store: list secrets rows: %w", err)
	}
	return out, nil
}

// Update overwrites mutable columns. Caller is responsible for bumping Version.
// Returns ErrNotFound if the secret does not exist.
func (r *SecretRepository) Update(ctx context.Context, s *Secret) error {
	if s.ID == "" {
		return errors.New("store: secret id is required")
	}
	if len(s.EncryptedPayload) == 0 || len(s.Nonce) == 0 {
		return errors.New("store: encrypted payload and nonce are required")
	}
	if s.UpdatedAt.IsZero() {
		s.UpdatedAt = nowUTC()
	}
	const q = `
UPDATE secrets SET
    folder_id = ?, encrypted_payload = ?, nonce = ?,
    version = ?, is_deleted = ?, updated_at = ?
WHERE id = ?;`
	res, err := r.db.ExecContext(ctx, q,
		nullable(s.FolderID), s.EncryptedPayload, s.Nonce,
		s.Version, boolToInt(s.IsDeleted), fmtTime(s.UpdatedAt), s.ID)
	if err != nil {
		return fmt.Errorf("store: update secret: %w", err)
	}
	return checkAffected(res)
}

// SoftDelete sets the tombstone flag. Returns ErrNotFound if absent.
func (r *SecretRepository) SoftDelete(ctx context.Context, id string) error {
	const q = `UPDATE secrets SET is_deleted = 1, updated_at = ? WHERE id = ?;`
	res, err := r.db.ExecContext(ctx, q, fmtTime(nowUTC()), id)
	if err != nil {
		return fmt.Errorf("store: soft delete secret: %w", err)
	}
	return checkAffected(res)
}

func scanSecret(s rowScanner) (Secret, error) {
	var (
		id               string
		folder           sql.NullString
		payload, nonce   []byte
		version, deleted int
		created, updated string
	)
	if err := s.Scan(&id, &folder, &payload, &nonce, &version, &deleted, &created, &updated); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return Secret{}, ErrNotFound
		}
		return Secret{}, fmt.Errorf("store: scan secret: %w", err)
	}
	createdAt, err := parseTime(created)
	if err != nil {
		return Secret{}, err
	}
	updatedAt, err := parseTime(updated)
	if err != nil {
		return Secret{}, err
	}
	return Secret{
		ID:               id,
		FolderID:         folder.String,
		EncryptedPayload: payload,
		Nonce:            nonce,
		Version:          version,
		IsDeleted:        deleted != 0,
		CreatedAt:        createdAt,
		UpdatedAt:        updatedAt,
	}, nil
}
