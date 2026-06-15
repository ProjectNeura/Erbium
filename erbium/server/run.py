from typing import Any, Literal

from uvicorn import run

from erbium.api import Node
from erbium.server.app import app, runtime


def run_server(port: int, *, host: str = "0.0.0.0", node_kwargs: dict[str, Any] | None = None,
               log_level: Literal["critical", "error", "warning", "info", "debug", "trace"] = "warning",
               access_log: bool = False) -> None:
    runtime.node = Node(**(node_kwargs or {}))
    run(app, host=host, port=port, log_level=log_level, access_log=access_log)
