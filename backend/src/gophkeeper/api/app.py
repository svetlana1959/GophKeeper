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
from gophkeeper.api.routers import secrets
from gophkeeper.infrastructure.adapters.database import SqlAlchemyAdapter
from gophkeeper.settings.settings import settings


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
    )
    app.state.database = database

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.api.trusted_hosts)

    register_exception_handlers(app)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(secrets.router)

    return app
