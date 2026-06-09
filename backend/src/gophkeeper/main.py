"""ASGI entrypoint.

``app`` is what uvicorn serves (``uvicorn gophkeeper.main:app``). ``run`` is the
console-script entry (``gophkeeper-server``) for running without a separate
uvicorn command line.
"""

import uvicorn

from gophkeeper.api.app import create_app
from gophkeeper.settings.settings import settings

app = create_app()


def run() -> None:
    uvicorn.run(
        "gophkeeper.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.reload,
        workers=settings.server.workers,
    )


if __name__ == "__main__":
    run()
