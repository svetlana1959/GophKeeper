"""Map domain errors to HTTP responses.

The domain raises vocabulary errors (``SecretNotFound``, ``VersionConflict``,
``DeviceNotFound``, ``DeviceAlreadyExists``); only this layer knows they become
404 and 409. Register once at app creation.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from gophkeeper.domain.errors import (
    AuthenticationError,
    DeviceAlreadyExists,
    DeviceNotFound,
    InvalidInvite,
    SecretNotFound,
    VersionConflict,
)


async def _unauthorized_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": str(exc)},
        headers={"WWW-Authenticate": "Bearer"},
    )


async def _bad_request_handler(request: Request, exc: InvalidInvite) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})


async def _not_found_handler(
    request: Request, exc: SecretNotFound | DeviceNotFound
) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})


async def _conflict_handler(
    request: Request, exc: VersionConflict | DeviceAlreadyExists
) -> JSONResponse:
    body = {"detail": str(exc)}
    if isinstance(exc, VersionConflict):
        body["expected_version"] = exc.expected
        body["actual_version"] = exc.actual
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=body,
    )


async def _integrity_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    # A unique/constraint violation that raced past a service-level pre-check
    # (e.g. two concurrent registrations of the same public key). It's a
    # conflict, not a server error — and we return a generic message rather than
    # the raw driver text so no SQL/schema detail leaks.
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "resource already exists"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AuthenticationError, _unauthorized_handler)  # type: ignore[arg-type]
    app.add_exception_handler(InvalidInvite, _bad_request_handler)  # type: ignore[arg-type]
    app.add_exception_handler(SecretNotFound, _not_found_handler)  # type: ignore[arg-type]
    app.add_exception_handler(DeviceNotFound, _not_found_handler)
    app.add_exception_handler(DeviceAlreadyExists, _conflict_handler)
    app.add_exception_handler(VersionConflict, _conflict_handler)  # type: ignore[arg-type]
    app.add_exception_handler(IntegrityError, _integrity_handler)  # type: ignore[arg-type]
