"""FastAPI dependencies — the composition root for a request.

The ``DatabaseAdapter`` is created once at startup and stored on ``app.state``.
Each request gets a fresh Unit of Work built from it, and a service wired to
that UoW. No global singletons: dependencies read from the app instance.
"""

from collections.abc import Callable
from uuid import UUID

from fastapi import Depends, Header, Request

from gophkeeper.domain.errors import AuthenticationError
from gophkeeper.domain.unit_of_work import UnitOfWork
from gophkeeper.infrastructure.adapters.database import DatabaseAdapter
from gophkeeper.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from gophkeeper.security.principal import AccountPrincipal, DevicePrincipal
from gophkeeper.services.account_auth_service import AccountAuthService
from gophkeeper.services.auth_service import AuthService


def get_database(request: Request) -> DatabaseAdapter:
    return request.app.state.database


def get_uow(database: DatabaseAdapter = Depends(get_database)) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(database)


def provide[Service](
    service: Callable[[UnitOfWork], Service],
) -> Callable[..., Service]:
    """Build a request dependency for any service constructed from a UnitOfWork.

    Every application service shares the shape ``Service(uow)``, so this one
    generic provider wires all of them — a new service needs no new function
    here. Use it directly in a router:

        service: SyncService = Depends(provide(SyncService))
    """

    def _provider(uow: UnitOfWork = Depends(get_uow)) -> Service:
        return service(uow)

    return _provider


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthenticationError("missing bearer token")
    return authorization.split(" ", 1)[1].strip()


async def get_principal(
    authorization: str | None = Header(default=None),
    service: AuthService = Depends(provide(AuthService)),
) -> DevicePrincipal:
    """Resolve the bearer session token on a request to its device principal.

    Use as a dependency on any protected endpoint:

        principal: DevicePrincipal = Depends(get_principal)
    """
    return await service.principal(_bearer_token(authorization))


def get_account_principal(
    authorization: str | None = Header(default=None),
    service: AccountAuthService = Depends(provide(AccountAuthService)),
) -> AccountPrincipal:
    """Resolve a web (account) session token to its account principal."""
    return service.principal(_bearer_token(authorization))


async def get_account_id(
    authorization: str | None = Header(default=None),
    account_auth: AccountAuthService = Depends(provide(AccountAuthService)),
    device_auth: AuthService = Depends(provide(AuthService)),
) -> UUID:
    """Resolve the caller's account id from *either* a web or a device token.

    Used by endpoints that only need "which account" — an invite can be minted by
    a logged-in web session or by an already-linked device. The device path still
    enforces the device lifecycle; the web path carries only the account.
    """
    token = _bearer_token(authorization)
    try:
        return account_auth.principal(token).account_id
    except AuthenticationError:
        return (await device_auth.principal(token)).account_id
