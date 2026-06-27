package store

import "errors"

// Errors the repositories return. The CLI matches on these instead of on
// SQLite-specific errors.
var (
	// ErrNotFound is returned when a row does not exist (get, or an update/
	// delete that affected zero rows).
	ErrNotFound = errors.New("store: not found")

	// ErrConflict is returned on a uniqueness/primary-key collision where an
	// upsert is not appropriate.
	ErrConflict = errors.New("store: conflict")
)
