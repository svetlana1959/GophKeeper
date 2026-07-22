package vault

import (
	"database/sql"
	"errors"
	"fmt"

	"github.com/svetlana1959/GophKeeper/cli/internal/syncstate"
)

type syncRepo struct{ db *sql.DB }

var _ syncstate.Repository = (*syncRepo)(nil)

func (r *syncRepo) GetState() (*syncstate.State, error) {
	var s syncstate.State
	err := r.db.QueryRow(`SELECT account_id, device_id, cursor FROM sync_state WHERE id = 1`).
		Scan(&s.AccountID, &s.DeviceID, &s.Cursor)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, syncstate.ErrNoState
	}
	if err != nil {
		return nil, fmt.Errorf("vault: get sync state: %w", err)
	}
	return &s, nil
}

func (r *syncRepo) SaveState(s *syncstate.State) error {
	_, err := r.db.Exec(`
		INSERT INTO sync_state (id, account_id, device_id, cursor)
		VALUES (1, ?, ?, ?)
		ON CONFLICT(id) DO UPDATE SET
			account_id = excluded.account_id,
			device_id  = excluded.device_id,
			cursor     = excluded.cursor`,
		s.AccountID, s.DeviceID, s.Cursor)
	if err != nil {
		return fmt.Errorf("vault: save sync state: %w", err)
	}
	return nil
}

// DeleteState forgets this device's account binding (device id + cursor) so Link
// can re-bind. Used by `goph link --force` after the device was removed
// server-side, which leaves the local binding stale but intact. Local secrets and
// the device keypair are untouched — a fresh sync re-pulls and re-pushes them.
func (r *syncRepo) DeleteState() error {
	if _, err := r.db.Exec(`DELETE FROM sync_state WHERE id = 1`); err != nil {
		return fmt.Errorf("vault: delete sync state: %w", err)
	}
	return nil
}

func (r *syncRepo) MarkDirty(secretID string) error {
	// Preserve server_version (the last reconciled version) — only flip dirty.
	_, err := r.db.Exec(`
		INSERT INTO secret_sync (secret_id, server_version, dirty)
		VALUES (?, 0, 1)
		ON CONFLICT(secret_id) DO UPDATE SET dirty = 1`, secretID)
	if err != nil {
		return fmt.Errorf("vault: mark dirty: %w", err)
	}
	return nil
}

func (r *syncRepo) MarkSynced(secretID string, serverVersion int) error {
	_, err := r.db.Exec(`
		INSERT INTO secret_sync (secret_id, server_version, dirty)
		VALUES (?, ?, 0)
		ON CONFLICT(secret_id) DO UPDATE SET
			server_version = excluded.server_version,
			dirty          = 0`, secretID, serverVersion)
	if err != nil {
		return fmt.Errorf("vault: mark synced: %w", err)
	}
	return nil
}

// ListDirty returns every secret needing a push: those explicitly marked dirty
// and those with no sync row yet (never synced — e.g. created before this device
// went online).
func (r *syncRepo) ListDirty() ([]syncstate.Dirty, error) {
	rows, err := r.db.Query(`
		SELECT s.id, COALESCE(ss.server_version, 0)
		FROM secrets s
		LEFT JOIN secret_sync ss ON ss.secret_id = s.id
		WHERE ss.secret_id IS NULL OR ss.dirty = 1
		ORDER BY s.id`)
	if err != nil {
		return nil, fmt.Errorf("vault: list dirty: %w", err)
	}
	defer rows.Close()

	var dirty []syncstate.Dirty
	for rows.Next() {
		var d syncstate.Dirty
		if err := rows.Scan(&d.SecretID, &d.ServerVersion); err != nil {
			return nil, fmt.Errorf("vault: scan dirty: %w", err)
		}
		dirty = append(dirty, d)
	}
	return dirty, rows.Err()
}
