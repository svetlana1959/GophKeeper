"""Application factory.

``create_app`` is the composition root: build the database adapter, wire it onto
the app, register middleware, exception handlers, and routers. The lifespan
context waits for the database on startup and disposes the pool on shutdown.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

from gophkeeper.api.errors import register_exception_handlers
from gophkeeper.api.routers import account, auth, device, enroll, sync
from gophkeeper.infrastructure.adapters.database import SqlAlchemyAdapter
from gophkeeper.settings.settings import settings

_TAGS_METADATA = [
    {
        "name": "auth",
        "description": (
            "Device authentication. A device proves it holds its private key via an "
            "**age challenge/response** (no key ever leaves the client) and receives a "
            "short-lived bearer session token used by the other endpoints."
        ),
    },
    {
        "name": "sync",
        "description": (
            "Zero-knowledge synchronization. Push opaque ciphertext under optimistic "
            "concurrency and pull the per-device delta since a cursor. The server never "
            "decrypts; it only relays and orders."
        ),
    },
    {
        "name": "accounts",
        "description": (
            "Web account authority. Register / log in with email + password and read "
            "the current account. Issues a bearer session that identifies the account "
            "but holds no key and can decrypt nothing."
        ),
    },
    {
        "name": "enroll",
        "description": "Link new devices into an account with single-use, expiring invite codes.",
    },
    {"name": "devices", "description": "Account device registry."},
    {"name": "health", "description": "Liveness."},
]


def create_app() -> FastAPI:
    logging.basicConfig(level=settings.run_settings.logging_level)

    database = SqlAlchemyAdapter(settings.database.url, settings.api.application_name)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        while True:
            try:
                await database.connect()
                break
            except Exception as exc:  # noqa: BLE001 — retry any connection failure
                logging.warning("database not ready, retrying: %s", exc)
                await asyncio.sleep(3)
        logging.info("database ready")
        yield
        await database.disconnect()

    app = FastAPI(
        title=f"{settings.api.application_name} API",
        description=settings.api.description,
        lifespan=lifespan,
        openapi_tags=_TAGS_METADATA,
    )
    app.state.database = database

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.api.trusted_hosts)

    register_exception_handlers(app)

    @app.get("/health", tags=["health"], summary="Liveness probe")
    async def health() -> dict[str, str]:
        """Return ``{"status": "ok"}`` once the app is serving."""
        return {"status": "ok"}

    app.include_router(auth.router)
    app.include_router(account.router)
    app.include_router(sync.router)
    app.include_router(enroll.router)
    app.include_router(device.router)

    return app
