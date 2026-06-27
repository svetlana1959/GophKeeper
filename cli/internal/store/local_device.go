package store

import (
	"context"
	"database/sql"
	"encoding/base64"
	"errors"
	"fmt"
)

// LocalDeviceRepository stores/reads this device's id + private-key blob.
//
// The blob is opaque to the store. The CLI passes it already PIN-encrypted, or
// as plaintext bytes when no PIN is set (protected by the 0600 file perms the
// Adapter enforces). The schema column is TEXT, so we base64-encode on write
// and decode on read; the original bytes round-trip exactly.
type LocalDeviceRepository struct {
	db *sql.DB
}

// Save upserts the single local device. device_id must reference an existing
// trusted_devices.id (FK), so create the trusted device first.
func (r *LocalDeviceRepository) Save(ctx context.Context, ld LocalDevice) error {
	if ld.DeviceID == "" {
		return errors.New("store: local device id is required")
	}
	if len(ld.PrivateKeyAtRest) == 0 {
		return errors.New("store: private key blob is required")
	}
	if ld.CreatedAt.IsZero() {
		ld.CreatedAt = nowUTC()
	}
	encoded := base64.StdEncoding.EncodeToString(ld.PrivateKeyAtRest)
	const q = `
INSERT INTO local_device (device_id, private_key_encrypted, created_at)
VALUES (?, ?, ?)
ON CONFLICT(device_id) DO UPDATE SET
    private_key_encrypted = excluded.private_key_encrypted;`
	if _, err := r.db.ExecContext(ctx, q, ld.DeviceID, encoded, fmtTime(ld.CreatedAt)); err != nil {
		return fmt.Errorf("store: save local device: %w", err)
	}
	return nil
}

// Get returns the local device, or ErrNotFound if init hasn't run yet.
func (r *LocalDeviceRepository) Get(ctx context.Context) (LocalDevice, error) {
	const q = `SELECT device_id, private_key_encrypted, created_at
	           FROM local_device LIMIT 1;`
	var id, encoded, created string
	if err := r.db.QueryRowContext(ctx, q).Scan(&id, &encoded, &created); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return LocalDevice{}, ErrNotFound
		}
		return LocalDevice{}, fmt.Errorf("store: get local device: %w", err)
	}
	raw, err := base64.StdEncoding.DecodeString(encoded)
	if err != nil {
		return LocalDevice{}, fmt.Errorf("store: decode local key: %w", err)
	}
	ts, err := parseTime(created)
	if err != nil {
		return LocalDevice{}, err
	}
	return LocalDevice{DeviceID: id, PrivateKeyAtRest: raw, CreatedAt: ts}, nil
}
