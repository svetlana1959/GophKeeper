"""SQLAlchemy Unit of Work — the adapter for the domain UoW port.

Owns one session for the duration of a use case and exposes the repositories
bound to it. Commit is explicit: the application service decides when work is
done. On exit we roll back if the block raised, and always close the session.
"""

from types import TracebackType
from typing import Self

from gophkeeper.domain.unit_of_work import UnitOfWork
from gophkeeper.infrastructure.adapters.database import DatabaseAdapter
from gophkeeper.infrastructure.repositories import (
    SqlAlchemySecretRepository,
    SqlAlchemyDeviceRepository,
)


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, database: DatabaseAdapter) -> None:
        self._database = database

    async def __aenter__(self) -> Self:
        self._session = self._database.session()

        """
        New repositories are added here
        """
        self.secrets = SqlAlchemySecretRepository(self._session)
        self.devices = SqlAlchemyDeviceRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            if exc_type is not None:
                await self.rollback()
        finally:
            await self._session.close()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
