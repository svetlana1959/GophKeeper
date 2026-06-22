package vault

import (
	"database/sql"
	"fmt"

	"github.com/svetlana1959/GophKeeper/cli/internal/domain"
)

type TrustedDeviceRepo struct {
	db *sql.DB
}

func NewTrustedDeviceRepo(db *sql.DB) *TrustedDeviceRepo {
	return &TrustedDeviceRepo{db: db}
}

func (r *TrustedDeviceRepo) Create(device *domain.TrustedDevice) error {
	if device == nil {
		return fmt.Errorf("trusted device is nil")
	}
	_, err := r.db.Exec(
		`INSERT INTO trusted_devices (id, device_name, public_key, is_active) VALUES (?, ?, ?, ?)`,
		device.ID,
		device.DeviceName,
		device.PublicKey,
		boolToInt(device.IsActive),
	)
	if err != nil {
		return fmt.Errorf("failed to create trusted device: %w", err)
	}
	return nil
}

func (r *TrustedDeviceRepo) Get(id string) (*domain.TrustedDevice, error) {
	device := &domain.TrustedDevice{}
	var isActive int
	row := r.db.QueryRow(`SELECT id, device_name, public_key, is_active, updated_at FROM trusted_devices WHERE id = ?`, id)
	if err := row.Scan(&device.ID, &device.DeviceName, &device.PublicKey, &isActive, &device.UpdatedAt); err != nil {
		if err == sql.ErrNoRows {
			return nil, domain.ErrTrustedDeviceNotFound
		}
		return nil, fmt.Errorf("failed to query trusted device: %w", err)
	}
	device.IsActive = isActive != 0
	return device, nil
}

func (r *TrustedDeviceRepo) List(activeOnly bool) ([]*domain.TrustedDevice, error) {
	query := `SELECT id, device_name, public_key, is_active, updated_at FROM trusted_devices`
	if activeOnly {
		query += ` WHERE is_active = 1`
	}
	rows, err := r.db.Query(query)
	if err != nil {
		return nil, fmt.Errorf("failed to list trusted devices: %w", err)
	}
	defer rows.Close()

	var devices []*domain.TrustedDevice
	for rows.Next() {
		device := &domain.TrustedDevice{}
		var isActive int
		if err := rows.Scan(&device.ID, &device.DeviceName, &device.PublicKey, &isActive, &device.UpdatedAt); err != nil {
			return nil, fmt.Errorf("failed to scan trusted device: %w", err)
		}
		device.IsActive = isActive != 0
		devices = append(devices, device)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("failed iterating trusted devices: %w", err)
	}
	return devices, nil
}

func (r *TrustedDeviceRepo) Update(device *domain.TrustedDevice) error {
	if device == nil {
		return fmt.Errorf("trusted device is nil")
	}
	result, err := r.db.Exec(
		`UPDATE trusted_devices SET device_name = ?, public_key = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?`,
		device.DeviceName,
		device.PublicKey,
		boolToInt(device.IsActive),
		device.ID,
	)
	if err != nil {
		return fmt.Errorf("failed to update trusted device: %w", err)
	}
	if rows, _ := result.RowsAffected(); rows == 0 {
		return domain.ErrTrustedDeviceNotFound
	}
	return nil
}

func (r *TrustedDeviceRepo) Activate(id string) error {
	result, err := r.db.Exec(`UPDATE trusted_devices SET is_active = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("failed to activate trusted device: %w", err)
	}
	if rows, _ := result.RowsAffected(); rows == 0 {
		return domain.ErrTrustedDeviceNotFound
	}
	return nil
}

func (r *TrustedDeviceRepo) Deactivate(id string) error {
	result, err := r.db.Exec(`UPDATE trusted_devices SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("failed to deactivate trusted device: %w", err)
	}
	if rows, _ := result.RowsAffected(); rows == 0 {
		return domain.ErrTrustedDeviceNotFound
	}
	return nil
}
