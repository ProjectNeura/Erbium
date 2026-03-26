from typing import Any

from uvicorn import run

from erbium.api import Node
from erbium.server.app import app, runtime

def run_server(port: int, *, host: str = "0.0.0.0", node_kwargs: dict[str, Any] | None = None) -> None:
    runtime.node = Node(**(node_kwargs or {}))
    run(app, host=host, port=port)
