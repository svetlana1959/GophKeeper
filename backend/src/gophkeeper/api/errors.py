"""Map domain errors to HTTP responses.

The domain raises vocabulary errors (``SecretNotFound``, ``VersionConflict``,``DeviceNotFound``, ``DeviceAlreadyExists``);
only this layer knows they become 404 and 409. Register once at app creation.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from gophkeeper.domain.errors import SecretNotFound, VersionConflict, DeviceNotFound, DeviceAlreadyExists


async def _not_found_handler(request: Request, exc: SecretNotFound | DeviceNotFound) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})


async def _conflict_handler(request: Request, exc: VersionConflict | DeviceAlreadyExists) -> JSONResponse:
    body = {"detail": str(exc)}
    if isinstance(exc, VersionConflict):
        body["expected_version"] = exc.expected
        body["actual_version"] = exc.actual
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=body,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(SecretNotFound, _not_found_handler)  # type: ignore[arg-type]
    app.add_exception_handler(DeviceNotFound, _not_found_handler)
    app.add_exception_handler(DeviceAlreadyExists, _conflict_handler)
    app.add_exception_handler(VersionConflict, _conflict_handler)  # type: ignore[arg-type]
