"""Application entrypoint.

Server mode is chosen from ``ENV``:

``debug``:
    uvicorn with auto-reload. Use for local development only.

``dev``, ``stage``, ``prod``, ``test``:
    gunicorn managing uvicorn workers. Use for deployed environments,
    local prod-like runs, and CI. Worker count defaults to
    (2 * CPU cores) + 1 and can be overridden with ``WEB_CONCURRENCY``.
"""

from __future__ import annotations

import sys

import uvicorn

from fourdrinier.app import app
from fourdrinier.core.settings import SETTINGS

__all__ = ["app", "debug", "prod", "worker_count"]


def worker_count() -> int:
    return SETTINGS.worker_count()


def debug() -> None:
    uvicorn.run(
        "fourdrinier.app:app",
        host=SETTINGS.host,
        port=SETTINGS.port,
        reload=True,
        log_level=SETTINGS.log_level,
    )


def prod() -> None:
    from gunicorn.app.wsgiapp import run

    bind = f"{SETTINGS.host}:{SETTINGS.port}"
    argv = [
        "gunicorn",
        "fourdrinier.app:app",
        "-k",
        "uvicorn.workers.UvicornWorker",
        "-w",
        str(SETTINGS.worker_count()),
        "-b",
        bind,
        "--access-logfile",
        "-",
        "--error-logfile",
        "-",
        "--timeout",
        str(SETTINGS.gunicorn_timeout),
        "--graceful-timeout",
        str(SETTINGS.gunicorn_graceful_timeout),
        "--max-requests",
        str(SETTINGS.gunicorn_max_requests),
        "--max-requests-jitter",
        str(SETTINGS.gunicorn_max_requests_jitter),
    ]

    if SETTINGS.gunicorn_preload:
        argv.append("--preload")

    sys.argv = argv
    run()


def run() -> None:
    if SETTINGS.is_debug_server:
        debug()
    else:
        prod()


if __name__ == "__main__":
    run()
