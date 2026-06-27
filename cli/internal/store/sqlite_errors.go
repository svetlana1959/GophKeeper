package store

import (
	"errors"

	sqlitelib "modernc.org/sqlite"
	sqlite3 "modernc.org/sqlite/lib"
)

// isUniqueViolation reports whether err is a SQLite UNIQUE/PRIMARY KEY conflict.
func isUniqueViolation(err error) bool {
	var serr *sqlitelib.Error
	if !errors.As(err, &serr) {
		return false
	}
	code := serr.Code()
	return code == sqlite3.SQLITE_CONSTRAINT_UNIQUE ||
		code == sqlite3.SQLITE_CONSTRAINT_PRIMARYKEY
}
