package store

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
)

// RecipientRepository: add / list / remove a recipient for a secret.
type RecipientRepository struct {
	db *sql.DB
}

// Add inserts (or updates the wrapped DEK for) a recipient. secret_id must
// reference an existing secret (FK).
func (r *RecipientRepository) Add(ctx context.Context, rec Recipient) error {
	if rec.SecretID == "" || rec.DeviceID == "" {
		return errors.New("store: secret id and device id are required")
	}
	if len(rec.EncryptedDEK) == 0 {
		return errors.New("store: encrypted dek is required")
	}
	const q = `
INSERT INTO secret_recipients (secret_id, device_id, encrypted_dek)
VALUES (?, ?, ?)
ON CONFLICT(secret_id, device_id) DO UPDATE SET
    encrypted_dek = excluded.encrypted_dek;`
	if _, err := r.db.ExecContext(ctx, q, rec.SecretID, rec.DeviceID, rec.EncryptedDEK); err != nil {
		return fmt.Errorf("store: add recipient: %w", err)
	}
	return nil
}

// ListBySecret returns all recipients for a secret, ordered by device id.
func (r *RecipientRepository) ListBySecret(ctx context.Context, secretID string) ([]Recipient, error) {
	const q = `SELECT secret_id, device_id, encrypted_dek
	           FROM secret_recipients WHERE secret_id = ? ORDER BY device_id;`
	rows, err := r.db.QueryContext(ctx, q, secretID)
	if err != nil {
		return nil, fmt.Errorf("store: list recipients: %w", err)
	}
	defer rows.Close()

	var out []Recipient
	for rows.Next() {
		var rec Recipient
		if err := rows.Scan(&rec.SecretID, &rec.DeviceID, &rec.EncryptedDEK); err != nil {
			return nil, fmt.Errorf("store: scan recipient: %w", err)
		}
		out = append(out, rec)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("store: list recipients rows: %w", err)
	}
	return out, nil
}

// Remove deletes one recipient. Returns ErrNotFound if the pair didn't exist.
func (r *RecipientRepository) Remove(ctx context.Context, secretID, deviceID string) error {
	res, err := r.db.ExecContext(ctx,
		`DELETE FROM secret_recipients WHERE secret_id = ? AND device_id = ?;`,
		secretID, deviceID)
	if err != nil {
		return fmt.Errorf("store: remove recipient: %w", err)
	}
	return checkAffected(res)
}
