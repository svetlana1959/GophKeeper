package vault

import (
	"database/sql"
	"fmt"

	"github.com/svetlana1959/GophKeeper/cli/internal/domain"
)

type LocalDeviceRepo struct {
	db *sql.DB
}

func NewLocalDeviceRepo(db *sql.DB) *LocalDeviceRepo {
	return &LocalDeviceRepo{db: db}
}

func (r *LocalDeviceRepo) Store(device *domain.LocalDevice) error {
	if device == nil {
		return fmt.Errorf("local device is nil")
	}
	_, err := r.db.Exec(
		`INSERT INTO local_device (device_id, private_key_encrypted) VALUES (?, ?)
		ON CONFLICT(device_id) DO UPDATE SET private_key_encrypted = excluded.private_key_encrypted`,
		device.DeviceID,
		device.PrivateKeyEncrypted,
	)
	if err != nil {
		return fmt.Errorf("failed to store local device: %w", err)
	}
	return nil
}

func (r *LocalDeviceRepo) Get() (*domain.LocalDevice, error) {
	device := &domain.LocalDevice{}
	row := r.db.QueryRow(`SELECT device_id, private_key_encrypted, created_at FROM local_device LIMIT 1`)
	if err := row.Scan(&device.DeviceID, &device.PrivateKeyEncrypted, &device.CreatedAt); err != nil {
		if err == sql.ErrNoRows {
			return nil, domain.ErrLocalDeviceNotFound
		}
		return nil, fmt.Errorf("failed to query local device: %w", err)
	}
	return device, nil
}

func (r *LocalDeviceRepo) Delete() error {
	result, err := r.db.Exec(`DELETE FROM local_device`)
	if err != nil {
		return fmt.Errorf("failed to delete local device: %w", err)
	}
	if rows, _ := result.RowsAffected(); rows == 0 {
		return domain.ErrLocalDeviceNotFound
	}
	return nil
}
