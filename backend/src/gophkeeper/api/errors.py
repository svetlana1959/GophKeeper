"""Map domain errors to HTTP responses.

The domain raises vocabulary errors (``SecretNotFound``, ``VersionConflict``);
only this layer knows they become 404 and 409. Register once at app creation.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from gophkeeper.domain.errors import SecretNotFound, VersionConflict


async def _not_found_handler(request: Request, exc: SecretNotFound) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})


async def _version_conflict_handler(request: Request, exc: VersionConflict) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "detail": str(exc),
            "expected_version": exc.expected,
            "actual_version": exc.actual,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(SecretNotFound, _not_found_handler)  # type: ignore[arg-type]
    app.add_exception_handler(VersionConflict, _version_conflict_handler)  # type: ignore[arg-type]
