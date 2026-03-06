from dataclasses import dataclass, asdict
from os.path import abspath
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from erbium.api import Scheduler, Job


@dataclass
class Runtime(object):
    homepage: str
    scheduler: Scheduler | None = None

    def get_scheduler(self) -> Scheduler:
        if self.scheduler:
            return self.scheduler
        raise RuntimeError("Scheduler not initialized")


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


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return runtime.homepage


@app.get("/running_containers")
async def get_running_containers() -> dict[str, Any]:
    return {k: asdict(v) for k, v in runtime.get_scheduler().running_containers.items()}


class JobModel(BaseModel):
    name: str
    requested_gpus: set[int]
    requested_run_time_hrs: float

@app.post("/schedule_job")
async def schedule_job(job: JobModel) -> dict[str, Any]:
    return asdict(runtime.get_scheduler().schedule(Job(job.name, job.requested_gpus, job.requested_run_time_hrs)))
