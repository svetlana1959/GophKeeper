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


@pytest.fixture
async def database():
    if not TEST_DATABASE_URL:
        pytest.skip("set TEST_DATABASE_URL to run integration tests")

    adapter = SqlAlchemyAdapter(TEST_DATABASE_URL, "gophkeeper-tests")
    await adapter.connect()

    # Start each test from a clean table.
    async with adapter.session() as session:
        await session.execute(text("DELETE FROM secrets"))
        await session.commit()

    yield adapter
    await adapter.disconnect()
