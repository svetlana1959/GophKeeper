"""Shared pytest fixtures and setup for the whole test suite."""

import asyncio
import sys

"""
Windows fix: asyncio's default event loop on Windows is the
``ProactorEventLoop``. It is great for subprocesses but has a known
incompatibility with asyncpg — under load it can tear down a socket and raise
a raw ``OSError``/``ConnectionResetError`` from deep inside
``windows_events.py`` instead of a clean, catchable error. This surfaces as
flaky integration tests with errors like:

    ConnectionResetError: [WinError 64] The specified network name is no
    longer available

The standard fix is to switch to ``SelectorEventLoop`` for the test session.
This has no effect on Linux/Mac, where asyncio already defaults to a
selector-based loop.
"""
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
