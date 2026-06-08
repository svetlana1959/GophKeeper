package vault

import (
	"database/sql"
	"errors"

	"github.com/svetlana1959/GophKeeper/cli/internal/domain"
)

// SecretRepo is the SQLite-backed implementation of domain.SecretRepository
// (#33). This is an EXAMPLE adapter: it wires the structure and proves the
// interface is satisfied, but the SQL is not written yet.
type SecretRepo struct {
	db *sql.DB
}

// Compile-time guarantee that SecretRepo satisfies the domain port. If the
// interface and this adapter ever drift, the build breaks here.
var _ domain.SecretRepository = (*SecretRepo)(nil)

// NewSecretRepo wires a repository over an already-open database handle.
func NewSecretRepo(db *sql.DB) *SecretRepo {
	return &SecretRepo{db: db}
}

var errNotImplemented = errors.New("vault: not implemented yet")

func (r *SecretRepo) Get(id string) (*domain.Secret, error)          { return nil, errNotImplemented }
func (r *SecretRepo) FindByName(name string) (*domain.Secret, error) { return nil, errNotImplemented }
func (r *SecretRepo) List(includeDeleted bool) ([]*domain.Secret, error) {
	return nil, errNotImplemented
}
func (r *SecretRepo) Save(s *domain.Secret) error { return errNotImplemented }
func (r *SecretRepo) Purge(id string) error       { return errNotImplemented }

// THIS IS EXAMPLE!
