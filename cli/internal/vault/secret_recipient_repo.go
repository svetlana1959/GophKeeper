package vault

import (
	"database/sql"
	"fmt"

	"github.com/svetlana1959/GophKeeper/cli/internal/domain"
)

type SecretRecipientRepo struct {
	db *sql.DB
}

func NewSecretRecipientRepo(db *sql.DB) *SecretRecipientRepo {
	return &SecretRecipientRepo{db: db}
}

func (r *SecretRecipientRepo) Add(recipient *domain.SecretRecipient) error {
	if recipient == nil {
		return fmt.Errorf("secret recipient is nil")
	}
	_, err := r.db.Exec(
		`INSERT INTO secret_recipients (secret_id, device_id, encrypted_dek) VALUES (?, ?, ?)
		ON CONFLICT(secret_id, device_id) DO UPDATE SET encrypted_dek = excluded.encrypted_dek`,
		recipient.SecretID,
		recipient.DeviceID,
		recipient.EncryptedDEK,
	)
	if err != nil {
		return fmt.Errorf("failed to add secret recipient: %w", err)
	}
	return nil
}

func (r *SecretRecipientRepo) Get(secretID, deviceID string) (*domain.SecretRecipient, error) {
	recipient := &domain.SecretRecipient{}
	row := r.db.QueryRow(`SELECT secret_id, device_id, encrypted_dek FROM secret_recipients WHERE secret_id = ? AND device_id = ?`, secretID, deviceID)
	if err := row.Scan(&recipient.SecretID, &recipient.DeviceID, &recipient.EncryptedDEK); err != nil {
		if err == sql.ErrNoRows {
			return nil, domain.ErrSecretRecipientNotFound
		}
		return nil, fmt.Errorf("failed to query secret recipient: %w", err)
	}
	return recipient, nil
}

func (r *SecretRecipientRepo) List(secretID string) ([]*domain.SecretRecipient, error) {
	rows, err := r.db.Query(`SELECT secret_id, device_id, encrypted_dek FROM secret_recipients WHERE secret_id = ?`, secretID)
	if err != nil {
		return nil, fmt.Errorf("failed to list secret recipients: %w", err)
	}
	defer rows.Close()

	var recipients []*domain.SecretRecipient
	for rows.Next() {
		recipient := &domain.SecretRecipient{}
		if err := rows.Scan(&recipient.SecretID, &recipient.DeviceID, &recipient.EncryptedDEK); err != nil {
			return nil, fmt.Errorf("failed to scan secret recipient: %w", err)
		}
		recipients = append(recipients, recipient)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("failed iterating secret recipients: %w", err)
	}
	return recipients, nil
}

func (r *SecretRecipientRepo) Remove(secretID, deviceID string) error {
	result, err := r.db.Exec(`DELETE FROM secret_recipients WHERE secret_id = ? AND device_id = ?`, secretID, deviceID)
	if err != nil {
		return fmt.Errorf("failed to remove secret recipient: %w", err)
	}
	if rows, _ := result.RowsAffected(); rows == 0 {
		return domain.ErrSecretRecipientNotFound
	}
	return nil
}
