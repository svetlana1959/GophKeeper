"""Fixtures for integration tests against a migrated PostgreSQL database."""

import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from gophkeeper.api.app import create_app
from gophkeeper.infrastructure.adapters.database import SqlAlchemyAdapter

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


async def _clear_database(adapter: SqlAlchemyAdapter) -> None:
    """Remove the complete account graph while preserving migration metadata."""
    async with adapter.session() as session:
        # accounts CASCADE covers identities, devices, invites, recipients, and
        # trust certs. secrets has a legacy TEXT account_id without an FK.
        await session.execute(text("TRUNCATE TABLE secrets, accounts RESTART IDENTITY CASCADE"))
        await session.commit()


@pytest.fixture
async def database():
    if not TEST_DATABASE_URL:
        pytest.skip("set TEST_DATABASE_URL to run integration tests")

    adapter = SqlAlchemyAdapter(TEST_DATABASE_URL, "gophkeeper-tests")
    await adapter.connect()
    await _clear_database(adapter)

    yield adapter

    await _clear_database(adapter)
    await adapter.disconnect()


@pytest.fixture
async def api_client(database):
    """Call the real FastAPI dependency graph against the test database."""
    app = create_app()
    app.state.database = database
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost") as client:
        yield client
