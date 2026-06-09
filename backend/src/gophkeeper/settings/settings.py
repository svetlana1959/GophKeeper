"""Application settings.

Dynaconf loads layered TOML (``settings.toml`` + ``settings.<env>.toml``) and
environment variables; the values are then validated into plain Pydantic models
so the rest of the app gets typed, autocomplete-friendly settings. We construct
each section explicitly rather than reflecting over fields — it is a handful of
lines and far easier to follow.

Switch environments with ``ENV`` (defaults to ``dev``). Override any value via
environment variables, e.g. ``GOPH_DATABASE__PASSWORD=...``.
"""

import os
from pathlib import Path

from dynaconf import Dynaconf
from pydantic import BaseModel

_CONFIG_DIR = Path(__file__).parent
_DEFAULT_ENV = "dev"


class DatabaseSettings(BaseModel):
    host: str
    port: int
    user: str
    password: str
    name: str

    @property
    def url(self) -> str:
        """Async SQLAlchemy URL (asyncpg driver)."""
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
        )


class APISettings(BaseModel):
    application_name: str
    description: str
    trusted_hosts: list[str]


class RunSettings(BaseModel):
    env: str = _DEFAULT_ENV
    logging_level: str = "INFO"


class ServerSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8080
    reload: bool = False
    workers: int = 1


class Settings(BaseModel):
    database: DatabaseSettings
    api: APISettings
    run_settings: RunSettings
    server: ServerSettings


_dynaconf = Dynaconf(
    settings_files=[
        str(_CONFIG_DIR / "settings.toml"),
        str(_CONFIG_DIR / "settings.dev.toml"),
    ],
    environments=True,
    envvar_prefix="GOPH",
    env_switcher="ENV",
    env=_DEFAULT_ENV,
    load_dotenv=False,
)


def _load() -> Settings:
    settings = Settings(
        database=DatabaseSettings(**_dynaconf.database),
        api=APISettings(**_dynaconf.api),
        run_settings=RunSettings(**_dynaconf.run_settings),
        server=ServerSettings(**_dynaconf.server),
    )
    settings.run_settings.env = os.environ.get("ENV", _DEFAULT_ENV)
    return settings


settings = _load()

__all__ = ["settings", "Settings"]
