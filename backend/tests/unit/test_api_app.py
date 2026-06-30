"""Unit tests for the FastAPI application factory."""

from gophkeeper.api import app as app_module


class FakeDatabaseAdapter:
    def __init__(self, failures_before_success: int = 0) -> None:
        self.failures_before_success = failures_before_success
        self.connect_calls = 0
        self.disconnect_calls = 0

    async def connect(self) -> None:
        self.connect_calls += 1
        if self.connect_calls <= self.failures_before_success:
            raise ConnectionError("postgres is still starting")

    async def disconnect(self) -> None:
        self.disconnect_calls += 1


def _fake_adapter_factory(adapter: FakeDatabaseAdapter):
    def factory(*_args, **_kwargs) -> FakeDatabaseAdapter:
        return adapter

    return factory


def test_create_app_wires_database_health_route_middleware_and_routers(monkeypatch) -> None:
    database = FakeDatabaseAdapter()
    monkeypatch.setattr(app_module, "SqlAlchemyAdapter", _fake_adapter_factory(database))

    app = app_module.create_app()
    paths = {route.path for route in app.routes}

    assert app.state.database is database
    assert "/health" in paths
    assert "/devices" in paths
    assert "/secrets" in paths
    assert app.user_middleware


async def test_lifespan_retries_database_connection_then_disconnects(monkeypatch) -> None:
    database = FakeDatabaseAdapter(failures_before_success=1)
    monkeypatch.setattr(app_module, "SqlAlchemyAdapter", _fake_adapter_factory(database))
    sleep_delays: list[int] = []

    async def fake_sleep(delay: int) -> None:
        sleep_delays.append(delay)

    monkeypatch.setattr(app_module.asyncio, "sleep", fake_sleep)
    app = app_module.create_app()

    async with app.router.lifespan_context(app):
        assert database.connect_calls == 2

    assert sleep_delays == [3]
    assert database.disconnect_calls == 1


async def test_health_endpoint_returns_ok_without_database_query(monkeypatch) -> None:
    database = FakeDatabaseAdapter()
    monkeypatch.setattr(app_module, "SqlAlchemyAdapter", _fake_adapter_factory(database))
    app = app_module.create_app()
    health_route = next(route for route in app.routes if route.path == "/health")

    response = await health_route.endpoint()

    assert response == {"status": "ok"}
    assert database.connect_calls == 0
