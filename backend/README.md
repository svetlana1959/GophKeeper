# GophKeeper Backend

The **blind backend** for GophKeeper: a zero-knowledge store that only ever sees
ciphertext. Clients encrypt on-device; the server holds opaque blobs plus the
metadata needed to sync them between a user's devices. It never holds a key and
cannot read a secret.

Stack: **FastAPI** · **SQLAlchemy (async) + asyncpg** · **PostgreSQL** ·
**Dynaconf** · **uv** · **dbmate** migrations.

## Layout

```text
backend/
├── db/migrations/                  # dbmate SQL migrations (up/down)
├── src/gophkeeper/
│   ├── main.py                     # ASGI entrypoint: app = create_app()
│   ├── settings/                   # Dynaconf + Pydantic settings, layered TOML
│   ├── domain/                     # Pure core — stdlib only
│   │   ├── secret.py               #   Secret aggregate + SecretRepository port
│   │   ├── unit_of_work.py         #   UnitOfWork port
│   │   └── errors.py               #   domain errors (DomainError, VersionConflict…)
│   ├── services/                   # Application use-cases (transaction boundary)
│   │   └── secret_service.py
│   ├── infrastructure/             # Adapters — implement the domain ports
│   │   ├── adapters/database.py    #   engine / connection pool
│   │   ├── unit_of_work.py         #   SqlAlchemyUnitOfWork
│   │   └── repositories/           #   SqlAlchemySecretRepository
│   └── api/                        # HTTP boundary
│       ├── app.py                  #   create_app(): composition root + lifespan
│       ├── deps.py                 #   request-scoped wiring (get_uow, provide)
│       ├── errors.py               #   domain error → HTTP status handlers
│       ├── routers/                #   endpoints, one module per resource
│       └── schemas/                #   DTOs (wire contract), one module per resource
└── tests/
    ├── unit/                       # pure domain rules — no database
    └── integration/                # adapters against a real PostgreSQL
```

## Architecture

The layering is hexagonal (ports & adapters). The **dependency rule**:
dependencies point inward toward `domain`, and `domain` depends on nothing but
the standard library — never SQLAlchemy, FastAPI, or asyncpg. This keeps the
business rules testable without a database and the storage/transport layers
replaceable.

Patterns in use:

- **Repository** (`SecretRepository`) — hides how/where data is stored.
- **Unit of Work** (`UnitOfWork`) — one transactional boundary per use case;
  commit is explicit, rollback-by-default on error.
- **Ports are `typing.Protocol`s** — adapters satisfy them structurally, so a
  test can pass a lightweight fake without inheriting anything.
- **Dependency injection** — FastAPI builds a fresh service per request via the
  generic `provide(...)` helper in `api/deps.py`.

`Secret` is the worked example, threaded through every layer. New aggregates
(`Device`, the device-authorization mailbox) follow the same shape: model + port
in `domain`, adapter in `infrastructure`, use-case in `services`, and a
`routers/<resource>.py` + `schemas/<resource>.py` pair in `api`.

### Request flow

```
HTTP → api/routers → api/schemas (validate DTO)
     → services (open UnitOfWork, drive the aggregate, commit)
     → infrastructure (repository SQL via the session)
     → domain (Secret enforces its own invariants)
```

Domain errors raised deep in that chain (e.g. `VersionConflict`) bubble up to the
handlers in `api/errors.py`, which map them to status codes (404, 409) — routers
contain no error-handling logic.

## Running locally

With Docker (Postgres + API + migrations):

```bash
make up        # build and start postgres + backend
make migrate   # apply migrations
make logs      # tail the API
```

The API is then at http://localhost:8080 (`/docs` for Swagger, `/health` for a
liveness check).

Without Docker (needs a reachable Postgres):

```bash
make install   # uv sync
make run       # uvicorn with --reload
make lint      # ruff format --check + ruff check
```

## Testing

```bash
make test              # everything (integration tests skip if no DB)
make test-unit         # domain rules only — fast, no database
make test-integration  # adapters against a real PostgreSQL
```

Integration tests skip unless `TEST_DATABASE_URL` is set, so a plain `make test`
never fails just because no database is running. To run them against the local
compose database:

```bash
make up && make migrate
export TEST_DATABASE_URL=postgresql+asyncpg://postgres:docker@localhost:5432/gophkeeper
make test-integration
```

## Migrations

Plain SQL via [dbmate](https://github.com/amacneil/dbmate), in `db/migrations/`.
Each file has a `-- migrate:up` and `-- migrate:down` section.

```bash
make migrate    # apply pending
make rollback   # revert the most recent
```
