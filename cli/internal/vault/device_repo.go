package vault

import (
	"database/sql"
	"errors"
	"fmt"
	"time"

	"github.com/svetlana1959/GophKeeper/cli/internal/device"
)

type deviceRepo struct{ db *sql.DB }

var _ device.Repository = (*deviceRepo)(nil)

func (r *deviceRepo) Save(d *device.Device) error {
	_, err := r.db.Exec(`
		INSERT INTO trusted_devices (id, device_name, public_key, is_active, updated_at)
		VALUES (?, ?, ?, ?, ?)
		ON CONFLICT(id) DO UPDATE SET
			device_name = excluded.device_name,
			public_key  = excluded.public_key,
			is_active   = excluded.is_active,
			updated_at  = excluded.updated_at`,
		d.ID, d.Name, d.PublicKey, boolToInt(d.Active), d.UpdatedAt.UnixNano())
	if err != nil {
		return fmt.Errorf("vault: save device: %w", err)
	}
	return nil
}

func (r *deviceRepo) Get(id string) (*device.Device, error) {
	return scanDevice(r.db.QueryRow(deviceCols+` WHERE id = ?`, id))
}

func (r *deviceRepo) FindByPublicKey(publicKey string) (*device.Device, error) {
	return scanDevice(r.db.QueryRow(deviceCols+` WHERE public_key = ?`, publicKey))
}

func (r *deviceRepo) List(includeInactive bool) ([]*device.Device, error) {
	q := deviceCols
	if !includeInactive {
		q += ` WHERE is_active = 1`
	}
	q += ` ORDER BY device_name`

	rows, err := r.db.Query(q)
	if err != nil {
		return nil, fmt.Errorf("vault: list devices: %w", err)
	}
	defer rows.Close()

	var devices []*device.Device
	for rows.Next() {
		d, err := scanDevice(rows)
		if err != nil {
			return nil, err
		}
		devices = append(devices, d)
	}
	return devices, rows.Err()
}

// SetActive flips the activity flag. It leaves updated_at untouched; callers that
// want to record the change time should Save the device with a new UpdatedAt.
func (r *deviceRepo) SetActive(id string, active bool) error {
	res, err := r.db.Exec(`UPDATE trusted_devices SET is_active = ? WHERE id = ?`, boolToInt(active), id)
	if err != nil {
		return fmt.Errorf("vault: set device active: %w", err)
	}
	return mustAffectOne(res, device.ErrNotFound)
}

const deviceCols = `SELECT id, device_name, public_key, is_active, updated_at FROM trusted_devices`

func scanDevice(sc rowScanner) (*device.Device, error) {
	var (
		d       device.Device
		active  int
		updated int64
	)
	err := sc.Scan(&d.ID, &d.Name, &d.PublicKey, &active, &updated)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, device.ErrNotFound
	}
	if err != nil {
		return nil, fmt.Errorf("vault: scan device: %w", err)
	}
	d.Active = active != 0
	d.UpdatedAt = time.Unix(0, updated).UTC()
	return &d, nil
}
