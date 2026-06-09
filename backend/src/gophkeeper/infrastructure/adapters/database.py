"""Database adapter.

The connection pool is a technical concern, so it sits behind an adapter rather
than being passed around as a raw engine. ``DatabaseAdapter`` is the contract
(lifecycle + session provisioning); ``SqlAlchemyAdapter`` is the SQLAlchemy/
asyncpg implementation. Anything that needs the database — the Unit of Work,
tests — depends on the contract, so the engine can be swapped or faked without
touching callers.

The engine is built lazily via ``connect()`` (called once at startup) rather
than in ``__init__``, so constructing the adapter is cheap and connecting can be
retried while Postgres comes up.
"""

from abc import ABC, abstractmethod

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

"""
Ideally it would sit in a separate "abstact db adapter" file, 
but tbh for such small codebase it doesn't make much of a difference

In the future, if you'll have more adapters you might wanna create adapter repository
and split this file into abastract and SqlAlchemy adapters
"""


class DatabaseAdapter(ABC):
    @abstractmethod
    async def connect(self) -> None:
        """Build the engine and verify connectivity. Idempotent."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Dispose the engine and its connection pool."""

    @abstractmethod
    def session(self) -> AsyncSession:
        """Open a new session for one unit of work."""


class SqlAlchemyAdapter(DatabaseAdapter):
    def __init__(self, url: str, application_name: str) -> None:
        self._url = url
        self._application_name = application_name
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def connect(self) -> None:
        if self._engine is not None:
            return
        engine = create_async_engine(
            self._url,
            connect_args={
                "server_settings": {"application_name": self._application_name}
            },
        )
        # Fail here (not on first query) if the database is unreachable.
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        self._engine = engine
        self._session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def disconnect(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    def session(self) -> AsyncSession:
        if self._session_factory is None:
            raise RuntimeError("database not connected; call connect() first")
        return self._session_factory()
