"""Fixtures for integration tests.

Integration tests run against a real PostgreSQL with the migrations applied.
Point ``TEST_DATABASE_URL`` at one (the local compose DB works), otherwise these
tests skip — so a plain ``make test`` never fails just because no DB is running.

    export TEST_DATABASE_URL=postgresql+asyncpg://postgres:docker@localhost:5432/gophkeeper
"""

import os

import pytest
from sqlalchemy import text

from gophkeeper.infrastructure.adapters.database import SqlAlchemyAdapter

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
APP_TABLES = (
    "secret_recipients",
    "invites",
    "secrets",
    "devices",
    "accounts",
)


@pytest.fixture
async def database():
    if not TEST_DATABASE_URL:
        pytest.skip("set TEST_DATABASE_URL to run integration tests")

    adapter = SqlAlchemyAdapter(TEST_DATABASE_URL, "gophkeeper-tests")
    await adapter.connect()

    yield adapter
    await adapter.disconnect()


@pytest.fixture(autouse=True)
async def clean_database(database):
    tables = ", ".join(APP_TABLES)
    # Restart identities and cascade through FK-dependent rows between tests.
    async with database.session() as session:
        await session.execute(text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE"))
        await session.commit()
