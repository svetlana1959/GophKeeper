"""Application factory.

``create_app`` is the composition root: build the database adapter, wire it onto
the app, register middleware, exception handlers, and routers. The lifespan
context waits for the database on startup and disposes the pool on shutdown.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

from gophkeeper.api.errors import register_exception_handlers
from gophkeeper.api.routers import account, auth, device, enroll, stats, sync, trust
from gophkeeper.infrastructure.adapters.database import SqlAlchemyAdapter
from gophkeeper.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from gophkeeper.services.device_service import DeviceService
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
    {
        "name": "trust",
        "description": (
            "Device trust graph. An append-only log of signed vouch/revoke certs the "
            "server relays but never verifies; each device recomputes the trusted set "
            "locally and reshares secrets only to it."
        ),
    },
    {
        "name": "stats",
        "description": "Account-scoped Dashboard statistics from zero-knowledge-safe metadata.",
    },
    {"name": "health", "description": "Liveness."},
]


async def _reap_expired_devices_forever(database: SqlAlchemyAdapter, interval: int) -> None:
    """Periodically delete devices past their self-declared expiry. Runs for the
    lifetime of the process; failures are logged and retried on the next tick so
    a transient DB blip never kills the sweep."""
    while True:
        await asyncio.sleep(interval)
        try:
            reaped = await DeviceService(SqlAlchemyUnitOfWork(database)).reap_expired()
            if reaped:
                logging.info("reaped %d expired device(s)", reaped)
        except Exception as exc:  # noqa: BLE001 — never let the sweep die
            logging.warning("device reaper failed: %s", exc)


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
        reaper = asyncio.create_task(
            _reap_expired_devices_forever(
                database, settings.security.device_reap_interval_seconds
            )
        )
        yield
        reaper.cancel()
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

    api_router = APIRouter(prefix="/api")

    @api_router.get("/health", tags=["health"], summary="Liveness probe")
    async def health() -> dict[str, str]:
        """Return ``{"status": "ok"}`` once the app is serving."""
        return {"status": "ok"}

    api_router.include_router(auth.router)
    api_router.include_router(account.router)
    api_router.include_router(sync.router)
    api_router.include_router(enroll.router)
    api_router.include_router(device.router)
    api_router.include_router(trust.router)
    api_router.include_router(stats.router)

    app.include_router(api_router)

    return app
