package vault

import (
	"database/sql"
	"errors"
	"fmt"

	"github.com/svetlana1959/GophKeeper/cli/internal/device"
)

type localRepo struct{ db *sql.DB }

var _ device.LocalRepository = (*localRepo)(nil)

// Save replaces the single local device row. The device_id must already exist in
// trusted_devices (enforced by the foreign key), so save the Device first.
func (r *localRepo) Save(ld *device.LocalDevice) error {
	tx, err := r.db.Begin()
	if err != nil {
		return fmt.Errorf("vault: begin: %w", err)
	}
	defer tx.Rollback()

	if _, err := tx.Exec(`DELETE FROM local_device`); err != nil {
		return fmt.Errorf("vault: clear local device: %w", err)
	}
	if _, err := tx.Exec(
		`INSERT INTO local_device (device_id, stored_key, pin_protected) VALUES (?, ?, ?)`,
		ld.DeviceID, ld.StoredKey, boolToInt(ld.PINProtected)); err != nil {
		return fmt.Errorf("vault: save local device: %w", err)
	}
	return tx.Commit()
}

func (r *localRepo) Get() (*device.LocalDevice, error) {
	var (
		ld  device.LocalDevice
		pin int
	)
	err := r.db.QueryRow(
		`SELECT device_id, stored_key, pin_protected FROM local_device LIMIT 1`).
		Scan(&ld.DeviceID, &ld.StoredKey, &pin)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, device.ErrNoLocalDevice
	}
	if err != nil {
		return nil, fmt.Errorf("vault: get local device: %w", err)
	}
	ld.PINProtected = pin != 0
	return &ld, nil
}
