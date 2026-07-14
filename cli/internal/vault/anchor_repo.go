package vault

import (
	"database/sql"
	"fmt"

	"github.com/svetlana1959/GophKeeper/cli/internal/trust"
)

type anchorRepo struct{ db *sql.DB }

var _ trust.AnchorRepository = (*anchorRepo)(nil)

func (r *anchorRepo) Save(a trust.Anchor) error {
	_, err := r.db.Exec(`
		INSERT INTO trust_anchors (device_id, enc_pub, sign_pub)
		VALUES (?, ?, ?)
		ON CONFLICT(device_id) DO UPDATE SET
			enc_pub  = excluded.enc_pub,
			sign_pub = excluded.sign_pub`,
		a.DeviceID, a.EncPub, a.SignPub)
	if err != nil {
		return fmt.Errorf("vault: save anchor: %w", err)
	}
	return nil
}

func (r *anchorRepo) List() ([]trust.Anchor, error) {
	rows, err := r.db.Query(`SELECT device_id, enc_pub, sign_pub FROM trust_anchors`)
	if err != nil {
		return nil, fmt.Errorf("vault: list anchors: %w", err)
	}
	defer rows.Close()

	var anchors []trust.Anchor
	for rows.Next() {
		var a trust.Anchor
		if err := rows.Scan(&a.DeviceID, &a.EncPub, &a.SignPub); err != nil {
			return nil, fmt.Errorf("vault: scan anchor: %w", err)
		}
		anchors = append(anchors, a)
	}
	return anchors, rows.Err()
}
