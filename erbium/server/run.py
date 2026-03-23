from os import PathLike
from typing import Any

from uvicorn import run

from erbium.api import Scheduler
from erbium.server.app import app, runtime

def run_server(port: int, root_dir: str | PathLike[str], input_dir: str | PathLike[str], *,
               host: str = "0.0.0.0", scheduler_kwargs: dict[str, Any] | None = None) -> None:
    runtime.scheduler = Scheduler(root_dir, input_dir, **(scheduler_kwargs or {}))
    run(app, host=host, port=port)
