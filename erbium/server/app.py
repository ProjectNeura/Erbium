from dataclasses import dataclass, asdict
from os.path import abspath
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from erbium.api import Node, Job, get_all_gpu_info


@dataclass
class Runtime(object):
    homepage: str
    node: Node | None = None

    def get_node(self) -> Node:
        if self.node:
            return self.node
        raise RuntimeError("Scheduler not initialized")


app: FastAPI = FastAPI(title="Erbium Server")
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


@app.get("/waitlist")
async def waitlist() -> dict[str, Any]:
    return {"wait_time_hrs": runtime.get_node().wait_time_hrs(), "jobs": runtime.get_node().waitlist()}


@app.get("/availability")
async def availability() -> dict[str, Any]:
    return {info.name: {
        "available": runtime.get_node().is_available(info), **asdict(info)
    } for device_id, info in get_all_gpu_info().items()}


class JobModel(BaseModel):
    name: str
    ssh_password: str
    requested_gpus: set[int]
    requested_run_time_hrs: float


@app.post("/join_waitlist")
async def join_waitlist(job: JobModel) -> None:
    runtime.get_node().join_waitlist(Job(job.name, job.ssh_password, job.requested_gpus, job.requested_run_time_hrs))


class JobQueryModel(BaseModel):
    name: str
    ssh_password: str


@app.post("/leave_waitlist")
async def leave_waitlist(job_query: JobQueryModel) -> None:
    runtime.get_node().leave_waitlist(job_query.name, job_query.ssh_password)
