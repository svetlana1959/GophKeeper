package vault

import (
	"database/sql"
	"fmt"
)

// rowScanner is satisfied by both *sql.Row and *sql.Rows, so a single scan
// helper serves Get/FindBy and List.
type rowScanner interface {
	Scan(dest ...any) error
}

func boolToInt(b bool) int {
	if b {
		return 1
	}
	return 0
}

// mustAffectOne maps a zero-row UPDATE/DELETE to notFound.
func mustAffectOne(res sql.Result, notFound error) error {
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("vault: rows affected: %w", err)
	}
	if n == 0 {
		return notFound
	}
	return nil
}
