"""FastAPI dependencies — the composition root for a request.

The ``DatabaseAdapter`` is created once at startup and stored on ``app.state``.
Each request gets a fresh Unit of Work built from it, and a service wired to
that UoW. No global singletons: dependencies read from the app instance.
"""

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
    """Identify the calling device from the ``X-Device-Id`` header.

    There is no account/auth layer yet (tracked separately), so this header is
    the only thing that says "who is asking" for issue #69's access checks. It
    is not a security boundary on its own — anyone can put any UUID in a
    header — it only lets the service layer look up *that device's* grants.
    Once real auth lands, this should be replaced by deriving the device from
    an authenticated session rather than trusting a bare header.
    """
    if x_device_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Device-Id header is required",
        )
    return x_device_id


def provide[Service](
    service: Callable[[UnitOfWork], Service],
) -> Callable[..., Service]:
    """Build a request dependency for any service constructed from a UnitOfWork.

    Every application service shares the shape ``Service(uow)``, so this one
    generic provider wires all of them — a new service needs no new function
    here. Use it directly in a router:

        service: SecretService = Depends(provide(SecretService))
    """

    def _provider(uow: UnitOfWork = Depends(get_uow)) -> Service:
        return service(uow)

    return _provider
