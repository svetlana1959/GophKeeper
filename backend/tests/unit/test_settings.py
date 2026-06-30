"""Unit tests for typed application settings."""

from gophkeeper.settings.settings import (
    APISettings,
    DatabaseSettings,
    RunSettings,
    ServerSettings,
    _load,
)


def test_database_settings_builds_async_sqlalchemy_url() -> None:
    database = DatabaseSettings(
        host="db.example.test",
        port=6543,
        user="gopher",
        password="secret",
        name="gophkeeper",
    )

    assert database.url == "postgresql+asyncpg://gopher:secret@db.example.test:6543/gophkeeper"


def test_run_and_server_settings_have_safe_defaults() -> None:
    run = RunSettings()
    server = ServerSettings()
    api = APISettings(
        application_name="GophKeeper", description="test", trusted_hosts=["localhost"]
    )

    assert run.env == "dev"
    assert run.logging_level == "INFO"
    assert server.host == "0.0.0.0"
    assert server.port == 8080
    assert server.reload is False
    assert server.workers == 1
    assert api.trusted_hosts == ["localhost"]


def test_load_uses_environment_name_from_env_variable(monkeypatch) -> None:
    monkeypatch.setenv("ENV", "test")

    loaded = _load()

    assert loaded.run_settings.env == "test"
    assert loaded.database.url.startswith("postgresql+asyncpg://")
