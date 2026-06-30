"""FastAPI dependencies."""

from collections.abc import Callable
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status

from gophkeeper.domain.unit_of_work import UnitOfWork
from gophkeeper.infrastructure.adapters.database import DatabaseAdapter
from gophkeeper.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


def get_database(request: Request) -> DatabaseAdapter:
    return request.app.state.database


def get_uow(database: DatabaseAdapter = Depends(get_database)) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(database)


def get_device_id(x_device_id: UUID | None = Header(default=None)) -> UUID:
    """Identify the calling device until real auth is added."""
    if x_device_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Device-Id header is required",
        )
    return x_device_id


def provide[Service](
    service: Callable[[UnitOfWork], Service],
) -> Callable[..., Service]:
    """Build a request dependency for a UnitOfWork-backed service."""

    def _provider(uow: UnitOfWork = Depends(get_uow)) -> Service:
        return service(uow)

    return _provider
