package vault

import (
	"database/sql"
	"fmt"

	"github.com/svetlana1959/GophKeeper/cli/internal/domain"
)

// SecretRepo is the SQLite-backed implementation of domain.SecretRepository.
type SecretRepo struct {
	db *sql.DB
}

// Compile-time guarantee that SecretRepo satisfies the domain port.
var _ domain.SecretRepository = (*SecretRepo)(nil)

// NewSecretRepo wires a repository over an already-open database handle.
func NewSecretRepo(db *sql.DB) *SecretRepo {
	return &SecretRepo{db: db}
}

func (r *SecretRepo) Get(id string) (*domain.Secret, error) {
	query := `SELECT id, name, folder_id, encrypted_payload, nonce, version, is_deleted, created_at, updated_at FROM secrets WHERE id = ?`
	row := r.db.QueryRow(query, id)
	secret := &domain.Secret{}
	var isDeleted int
	if err := row.Scan(&secret.ID, &secret.Name, &secret.FolderID, &secret.Payload, &secret.Nonce, &secret.Version, &isDeleted, &secret.CreatedAt, &secret.UpdatedAt); err != nil {
		if err == sql.ErrNoRows {
			return nil, domain.ErrSecretNotFound
		}
		return nil, fmt.Errorf("failed to query secret: %w", err)
	}
	secret.Deleted = isDeleted != 0
	return secret, nil
}

func (r *SecretRepo) FindByName(name string) (*domain.Secret, error) {
	query := `SELECT id, name, folder_id, encrypted_payload, nonce, version, is_deleted, created_at, updated_at FROM secrets WHERE name = ?`
	row := r.db.QueryRow(query, name)
	secret := &domain.Secret{}
	var isDeleted int
	if err := row.Scan(&secret.ID, &secret.Name, &secret.FolderID, &secret.Payload, &secret.Nonce, &secret.Version, &isDeleted, &secret.CreatedAt, &secret.UpdatedAt); err != nil {
		if err == sql.ErrNoRows {
			return nil, domain.ErrSecretNotFound
		}
		return nil, fmt.Errorf("failed to query secret by name: %w", err)
	}
	secret.Deleted = isDeleted != 0
	return secret, nil
}

func (r *SecretRepo) List(includeDeleted bool) ([]*domain.Secret, error) {
	query := `SELECT id, name, folder_id, encrypted_payload, nonce, version, is_deleted, created_at, updated_at FROM secrets`
	if !includeDeleted {
		query += ` WHERE is_deleted = 0`
	}
	rows, err := r.db.Query(query)
	if err != nil {
		return nil, fmt.Errorf("failed to query secrets: %w", err)
	}
	defer rows.Close()

	var secrets []*domain.Secret
	for rows.Next() {
		secret := &domain.Secret{}
		var isDeleted int
		if err := rows.Scan(&secret.ID, &secret.Name, &secret.FolderID, &secret.Payload, &secret.Nonce, &secret.Version, &isDeleted, &secret.CreatedAt, &secret.UpdatedAt); err != nil {
			return nil, fmt.Errorf("failed to scan secret row: %w", err)
		}
		secret.Deleted = isDeleted != 0
		secrets = append(secrets, secret)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("failed iterating secret rows: %w", err)
	}
	return secrets, nil
}

func (r *SecretRepo) Save(s *domain.Secret) error {
	if s == nil {
		return fmt.Errorf("secret is nil")
	}
	if s.Version == 0 {
		s.Version = 1
	}
	query := `INSERT INTO secrets (id, name, folder_id, encrypted_payload, nonce, version, is_deleted) VALUES (?, ?, ?, ?, ?, ?, ?)
		ON CONFLICT(id) DO UPDATE SET name = excluded.name, folder_id = excluded.folder_id, encrypted_payload = excluded.encrypted_payload, nonce = excluded.nonce, version = excluded.version, is_deleted = excluded.is_deleted, updated_at = CURRENT_TIMESTAMP`
	_, err := r.db.Exec(query, s.ID, s.Name, s.FolderID, s.Payload, s.Nonce, s.Version, boolToInt(s.Deleted))
	if err != nil {
		return fmt.Errorf("failed to save secret: %w", err)
	}
	return nil
}

func (r *SecretRepo) Purge(id string) error {
	result, err := r.db.Exec(`DELETE FROM secrets WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("failed to purge secret: %w", err)
	}
	if count, _ := result.RowsAffected(); count == 0 {
		return domain.ErrSecretNotFound
	}
	return nil
}

func boolToInt(value bool) int {
	if value {
		return 1
	}
	return 0
}
