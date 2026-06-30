"""Unit test for the command-line server entrypoint.

uvicorn.run is replaced with a small fake, so this checks only that GophKeeper
passes the configured application path and server settings to Uvicorn.
"""

from gophkeeper import main


def test_run_passes_configured_server_settings_to_uvicorn(monkeypatch) -> None:
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def fake_run(*args, **kwargs) -> None:
        calls.append((args, kwargs))

    monkeypatch.setattr(main.uvicorn, "run", fake_run)

    main.run()

    args, kwargs = calls[0]
    assert args == ("gophkeeper.main:app",)
    assert kwargs == {
        "host": main.settings.server.host,
        "port": main.settings.server.port,
        "reload": main.settings.server.reload,
        "workers": main.settings.server.workers,
    }
