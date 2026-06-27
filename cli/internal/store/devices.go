package store

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
)

// DeviceRepository is CRUD + activate/deactivate over trusted_devices.
type DeviceRepository struct {
	db *sql.DB
}

// Save inserts a new device or updates an existing one (upsert by id).
func (r *DeviceRepository) Save(ctx context.Context, d TrustedDevice) error {
	if d.ID == "" {
		return errors.New("store: device id is required")
	}
	if d.UpdatedAt.IsZero() {
		d.UpdatedAt = nowUTC()
	}
	const q = `
INSERT INTO trusted_devices (id, device_name, public_key, is_active, updated_at)
VALUES (?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
    device_name = excluded.device_name,
    public_key  = excluded.public_key,
    is_active   = excluded.is_active,
    updated_at  = excluded.updated_at;`
	if _, err := r.db.ExecContext(ctx, q,
		d.ID, d.Name, d.PublicKey, boolToInt(d.IsActive), fmtTime(d.UpdatedAt)); err != nil {
		return fmt.Errorf("store: save device: %w", err)
	}
	return nil
}

// GetByID returns a device or ErrNotFound.
func (r *DeviceRepository) GetByID(ctx context.Context, id string) (TrustedDevice, error) {
	const q = `SELECT id, device_name, public_key, is_active, updated_at
	           FROM trusted_devices WHERE id = ?;`
	return scanDevice(r.db.QueryRowContext(ctx, q, id))
}

// List returns all devices ordered by name.
func (r *DeviceRepository) List(ctx context.Context) ([]TrustedDevice, error) {
	const q = `SELECT id, device_name, public_key, is_active, updated_at
	           FROM trusted_devices ORDER BY device_name;`
	rows, err := r.db.QueryContext(ctx, q)
	if err != nil {
		return nil, fmt.Errorf("store: list devices: %w", err)
	}
	defer rows.Close()

	var out []TrustedDevice
	for rows.Next() {
		d, err := scanDevice(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, d)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("store: list devices rows: %w", err)
	}
	return out, nil
}

// Delete removes a device (cascades to local_device). ErrNotFound if absent.
func (r *DeviceRepository) Delete(ctx context.Context, id string) error {
	res, err := r.db.ExecContext(ctx, `DELETE FROM trusted_devices WHERE id = ?;`, id)
	if err != nil {
		return fmt.Errorf("store: delete device: %w", err)
	}
	return checkAffected(res)
}

// Activate / Deactivate flip the revocation flag.
func (r *DeviceRepository) Activate(ctx context.Context, id string) error {
	return r.setActive(ctx, id, true)
}
func (r *DeviceRepository) Deactivate(ctx context.Context, id string) error {
	return r.setActive(ctx, id, false)
}

func (r *DeviceRepository) setActive(ctx context.Context, id string, active bool) error {
	const q = `UPDATE trusted_devices SET is_active = ?, updated_at = ? WHERE id = ?;`
	res, err := r.db.ExecContext(ctx, q, boolToInt(active), fmtTime(nowUTC()), id)
	if err != nil {
		return fmt.Errorf("store: set active: %w", err)
	}
	return checkAffected(res)
}

func scanDevice(s rowScanner) (TrustedDevice, error) {
	var (
		id, name, pub, updated string
		active                 int
	)
	if err := s.Scan(&id, &name, &pub, &active, &updated); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return TrustedDevice{}, ErrNotFound
		}
		return TrustedDevice{}, fmt.Errorf("store: scan device: %w", err)
	}
	ts, err := parseTime(updated)
	if err != nil {
		return TrustedDevice{}, err
	}
	return TrustedDevice{
		ID:        id,
		Name:      name,
		PublicKey: pub,
		IsActive:  active != 0,
		UpdatedAt: ts,
	}, nil
}
