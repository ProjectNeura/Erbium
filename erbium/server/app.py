from dataclasses import dataclass
from os.path import abspath
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from erbium.api import Scheduler


@dataclass
class Runtime(object):
    homepage: str
    scheduler: Scheduler | None = None

    def get_scheduler(self) -> Scheduler:
        if self.scheduler:
            return self.scheduler
        raise RuntimeError("Scheduler not initialized")

    def running_containers(self) -> dict[str, Any]:
        return self.get_scheduler().running_containers


app: FastAPI = FastAPI(title="LEADS VeC Remote Analyst")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

runtime: Runtime = Runtime("")

with open(f"{abspath(__file__)[:-6]}assets/index.html") as f:
    runtime.homepage = f.read()


@app.get("/")
def index() -> str:
    return runtime.homepage


@app.get("/running_containers")
def get_running_containers() -> dict[str, Any]:
    return runtime.running_containers()
