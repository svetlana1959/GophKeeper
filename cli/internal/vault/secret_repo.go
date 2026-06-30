package vault

import (
	"database/sql"
	"errors"
	"fmt"
	"time"

	"github.com/svetlana1959/GophKeeper/cli/internal/device"
	"github.com/svetlana1959/GophKeeper/cli/internal/secret"
)

type secretRepo struct{ db *sql.DB }

var _ secret.Repository = (*secretRepo)(nil)

// Save upserts the secret and replaces its recipient set in one transaction —
// recipients are part of the Secret aggregate. Every recipient public key must
// belong to a known trusted device; an unknown one fails with device.ErrNotFound.
func (r *secretRepo) Save(s *secret.Secret) error {
	tx, err := r.db.Begin()
	if err != nil {
		return fmt.Errorf("vault: begin: %w", err)
	}
	defer tx.Rollback()

	if _, err := tx.Exec(`
		INSERT INTO secrets (id, folder_id, name, payload, version, is_deleted, updated_at)
		VALUES (?, ?, ?, ?, ?, ?, ?)
		ON CONFLICT(id) DO UPDATE SET
			folder_id  = excluded.folder_id,
			name       = excluded.name,
			payload    = excluded.payload,
			version    = excluded.version,
			is_deleted = excluded.is_deleted,
			updated_at = excluded.updated_at`,
		s.ID, s.FolderID, s.Name, s.Payload, s.Version, boolToInt(s.Deleted), s.UpdatedAt.UnixNano()); err != nil {
		return fmt.Errorf("vault: save secret: %w", err)
	}

	if _, err := tx.Exec(`DELETE FROM secret_recipients WHERE secret_id = ?`, s.ID); err != nil {
		return fmt.Errorf("vault: clear recipients: %w", err)
	}
	for _, pub := range s.Recipients {
		var deviceID string
		err := tx.QueryRow(`SELECT id FROM trusted_devices WHERE public_key = ?`, pub).Scan(&deviceID)
		if errors.Is(err, sql.ErrNoRows) {
			return fmt.Errorf("vault: recipient %q: %w", pub, device.ErrNotFound)
		}
		if err != nil {
			return fmt.Errorf("vault: resolve recipient: %w", err)
		}
		if _, err := tx.Exec(
			`INSERT INTO secret_recipients (secret_id, device_id) VALUES (?, ?)`, s.ID, deviceID); err != nil {
			return fmt.Errorf("vault: add recipient: %w", err)
		}
	}
	return tx.Commit()
}

func (r *secretRepo) Get(id string) (*secret.Secret, error) {
	s, err := scanSecret(r.db.QueryRow(secretCols+` WHERE id = ?`, id))
	if err != nil {
		return nil, err
	}
	return r.withRecipients(s)
}

func (r *secretRepo) FindByName(name string) (*secret.Secret, error) {
	s, err := scanSecret(r.db.QueryRow(secretCols+` WHERE name = ?`, name))
	if err != nil {
		return nil, err
	}
	return r.withRecipients(s)
}

func (r *secretRepo) List(includeDeleted bool) ([]*secret.Secret, error) {
	q := secretCols
	if !includeDeleted {
		q += ` WHERE is_deleted = 0`
	}
	q += ` ORDER BY name`

	rows, err := r.db.Query(q)
	if err != nil {
		return nil, fmt.Errorf("vault: list secrets: %w", err)
	}
	defer rows.Close()

	var secrets []*secret.Secret
	for rows.Next() {
		s, err := scanSecret(rows)
		if err != nil {
			return nil, err
		}
		secrets = append(secrets, s)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	// Release the single connection before hydrating recipients, which queries
	// again (SetMaxOpenConns(1) would otherwise deadlock).
	rows.Close()

	for _, s := range secrets {
		if _, err := r.withRecipients(s); err != nil {
			return nil, err
		}
	}
	return secrets, nil
}

// Purge hard-deletes a secret; ON DELETE CASCADE clears its recipients. A soft
// delete is Secret.Delete followed by Save.
func (r *secretRepo) Purge(id string) error {
	res, err := r.db.Exec(`DELETE FROM secrets WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("vault: purge secret: %w", err)
	}
	return mustAffectOne(res, secret.ErrNotFound)
}

const secretCols = `SELECT id, folder_id, name, payload, version, is_deleted, updated_at FROM secrets`

func scanSecret(sc rowScanner) (*secret.Secret, error) {
	var (
		s       secret.Secret
		folder  sql.NullString
		deleted int
		updated int64
	)
	err := sc.Scan(&s.ID, &folder, &s.Name, &s.Payload, &s.Version, &deleted, &updated)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, secret.ErrNotFound
	}
	if err != nil {
		return nil, fmt.Errorf("vault: scan secret: %w", err)
	}
	s.FolderID = folder.String
	s.Deleted = deleted != 0
	s.UpdatedAt = time.Unix(0, updated).UTC()
	return &s, nil
}

func (r *secretRepo) withRecipients(s *secret.Secret) (*secret.Secret, error) {
	rows, err := r.db.Query(`
		SELECT d.public_key
		FROM secret_recipients sr
		JOIN trusted_devices d ON d.id = sr.device_id
		WHERE sr.secret_id = ?
		ORDER BY d.public_key`, s.ID)
	if err != nil {
		return nil, fmt.Errorf("vault: load recipients: %w", err)
	}
	defer rows.Close()

	s.Recipients = nil
	for rows.Next() {
		var pub string
		if err := rows.Scan(&pub); err != nil {
			return nil, fmt.Errorf("vault: scan recipient: %w", err)
		}
		s.Recipients = append(s.Recipients, pub)
	}
	return s, rows.Err()
}
