"""Map domain errors to HTTP responses."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from gophkeeper.domain.errors import (
    AccessDenied,
    AccessRequestAlreadyPending,
    AccessRequestNotFound,
    AccessRequestNotPending,
    DeviceAlreadyExists,
    DeviceNotFound,
    NotSecretOwner,
    SecretNotFound,
    VersionConflict,
)

_NotFoundError = SecretNotFound | DeviceNotFound | AccessRequestNotFound
_ConflictError = (
    VersionConflict | DeviceAlreadyExists | AccessRequestAlreadyPending | AccessRequestNotPending
)
_ForbiddenError = AccessDenied | NotSecretOwner


async def _not_found_handler(request: Request, exc: _NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})


async def _conflict_handler(request: Request, exc: _ConflictError) -> JSONResponse:
    body = {"detail": str(exc)}
    if isinstance(exc, VersionConflict):
        body["expected_version"] = exc.expected
        body["actual_version"] = exc.actual
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=body,
    )


async def _forbidden_handler(request: Request, exc: _ForbiddenError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": str(exc)})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(SecretNotFound, _not_found_handler)  # type: ignore[arg-type]
    app.add_exception_handler(DeviceNotFound, _not_found_handler)  # type: ignore[arg-type]
    app.add_exception_handler(AccessRequestNotFound, _not_found_handler)  # type: ignore[arg-type]
    app.add_exception_handler(DeviceAlreadyExists, _conflict_handler)  # type: ignore[arg-type]
    app.add_exception_handler(VersionConflict, _conflict_handler)  # type: ignore[arg-type]
    app.add_exception_handler(AccessRequestAlreadyPending, _conflict_handler)  # type: ignore[arg-type]
    app.add_exception_handler(AccessRequestNotPending, _conflict_handler)  # type: ignore[arg-type]
    app.add_exception_handler(AccessDenied, _forbidden_handler)  # type: ignore[arg-type]
    app.add_exception_handler(NotSecretOwner, _forbidden_handler)  # type: ignore[arg-type]
