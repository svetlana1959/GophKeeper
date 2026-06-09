"""Unit of Work port (a ``typing.Protocol``).

A use case runs inside one transactional boundary. The UoW exposes the
repositories that share that boundary and the commit/rollback controls. It lives
in the domain and references only repository *ports* — never SQLAlchemy. The
adapter is ``gophkeeper.infrastructure.unit_of_work.SqlAlchemyUnitOfWork``; a
test can supply a fake that structurally matches this protocol.

As more aggregates are added, expose their repositories here alongside
``secrets`` (e.g. ``devices``) so a single use case can touch several within one
transaction.
"""

from types import TracebackType
from typing import Protocol, Self

from gophkeeper.domain.secret import SecretRepository


class UnitOfWork(Protocol):
    """
    Add new repositories here and in the infrastructure as well
    """

    secrets: SecretRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
