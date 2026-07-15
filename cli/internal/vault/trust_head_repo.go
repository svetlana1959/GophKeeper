package vault

import (
	"database/sql"
	"fmt"

	"github.com/svetlana1959/GophKeeper/cli/internal/trust"
)

type trustHeadRepo struct{ db *sql.DB }

var _ trust.TrustHeadRepository = (*trustHeadRepo)(nil)

func (r *trustHeadRepo) List() (map[string]trust.Head, error) {
	rows, err := r.db.Query(`SELECT issuer_id, seq, hash FROM trust_heads`)
	if err != nil {
		return nil, fmt.Errorf("vault: list trust heads: %w", err)
	}
	defer rows.Close()

	heads := map[string]trust.Head{}
	for rows.Next() {
		var id string
		var h trust.Head
		if err := rows.Scan(&id, &h.Seq, &h.Hash); err != nil {
			return nil, fmt.Errorf("vault: scan trust head: %w", err)
		}
		heads[id] = h
	}
	return heads, rows.Err()
}

func (r *trustHeadRepo) Save(issuerID string, h trust.Head) error {
	_, err := r.db.Exec(`
		INSERT INTO trust_heads (issuer_id, seq, hash)
		VALUES (?, ?, ?)
		ON CONFLICT(issuer_id) DO UPDATE SET
			seq  = excluded.seq,
			hash = excluded.hash`,
		issuerID, h.Seq, h.Hash)
	if err != nil {
		return fmt.Errorf("vault: save trust head: %w", err)
	}
	return nil
}
