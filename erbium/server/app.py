from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from erbium.api import Scheduler


@dataclass
class Runtime(object):
    scheduler: Scheduler | None = None

    def get_scheduler(self) -> Scheduler:
        if self.scheduler:
            return self.scheduler
        raise RuntimeError("Scheduler not initialized")

    def running_containers(self) -> dict[str, Any]:
        return self.scheduler.running_containers


app: FastAPI = FastAPI(title="LEADS VeC Remote Analyst")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

runtime: Runtime = Runtime()

@app.get("/running_containers")
def get_running_containers() -> dict[str, Any]:
    return runtime.running_containers()