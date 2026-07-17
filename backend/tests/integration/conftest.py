"""Fixtures for integration tests against a migrated PostgreSQL database.

Isolation strategy: every test runs inside one transaction that is never
committed, and is rolled back when the test ends. That single mechanism buys both
axes of safety a parallel suite needs:

* **test-to-test** — the rollback erases everything the test wrote, so the next
  test on this worker starts from the migrated baseline. No truncation, no
  cleanup ordering to get wrong.
* **worker-to-worker** — uncommitted rows are invisible to other connections
  under READ COMMITTED, so ``pytest -n auto`` workers cannot observe (or wipe)
  each other's data. They share one database safely.

The seam that makes this possible is ``DatabaseAdapter``: the Unit of Work
depends on the abstract contract, so a test can hand the application a session
factory bound to *its* connection (see ``_RollbackAdapter``). The application
still calls ``commit()`` for real — ``join_transaction_mode="create_savepoint"``
turns it into a SAVEPOINT release, so committed-then-read flows behave normally
while the outer transaction stays open and discardable. See SQLAlchemy's
"Joining a Session into an External Transaction (such as for test suites)".

The trade-off: every session in a test rides one connection, so this cannot
exercise genuine concurrency (two writers racing on a version check). A test that
needs real commits from separate connections needs a different fixture — the
equivalent of Django's TransactionTestCase — rather than this one.
"""

import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from gophkeeper.api.app import create_app
from gophkeeper.infrastructure.adapters.database import DatabaseAdapter

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


class _RollbackAdapter(DatabaseAdapter):
    """A DatabaseAdapter whose sessions join the test's open transaction.

    Implements the same contract the application depends on, so the code under
    test is wired exactly as in production — it just cannot escape the
    transaction we intend to throw away.
    """

    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def connect(self) -> None:
        """No-op: the test fixture owns the connection's lifecycle."""

    async def disconnect(self) -> None:
        """No-op: the test fixture owns the connection's lifecycle."""

    def session(self) -> AsyncSession:
        return AsyncSession(
            bind=self._connection,
            expire_on_commit=False,  # mirrors SqlAlchemyAdapter
            join_transaction_mode="create_savepoint",
        )


@pytest.fixture(scope="session")
def engine():
    """One engine per worker, built once.

    Sync and NullPool'd on purpose: with no pooled connections the engine holds
    no event-loop state, so it is safe to share across per-test loops while each
    test still opens its connection on its own loop.
    """
    if not TEST_DATABASE_URL:
        pytest.skip("set TEST_DATABASE_URL to run integration tests")
    return create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)


@pytest.fixture
async def connection(engine):
    """A connection with an open transaction that is always rolled back."""
    async with engine.connect() as conn:
        transaction = await conn.begin()
        try:
            yield conn
        finally:
            await transaction.rollback()


@pytest.fixture
async def database(connection) -> DatabaseAdapter:
    """The application's database port, bound to this test's transaction."""
    return _RollbackAdapter(connection)


@pytest.fixture
async def api_client(database):
    """Call the real FastAPI dependency graph against the test database.

    ``create_app`` builds its own adapter for production, but httpx's
    ASGITransport does not run lifespan events, so that adapter never connects
    and this override is what the dependency graph resolves. Load-bearing: if
    lifespan is ever run here, the app would talk to its own pool and escape the
    test's transaction.

    TODO: look into rewriting create_app

    The base URL carries the ``/api`` mount, so tests and helpers address
    endpoints by their router path — ``/stats/overview``, not
    ``/api/stats/overview``.
    """
    app = create_app()
    app.state.database = database
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost/api") as client:
        yield client
