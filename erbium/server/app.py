from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from erbium.api import Node, Job, get_all_gpu_info


@dataclass
class Runtime(object):
    homepage: str
    dashboard: str
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

runtime: Runtime = Runtime("", "")

assets_dir = Path(__file__).with_name("assets")
runtime.homepage = (assets_dir / "index.html").read_text()
runtime.dashboard = (assets_dir / "dash.html").read_text()


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return runtime.homepage


@app.get("/dash", response_class=HTMLResponse)
async def dash() -> str:
    return runtime.dashboard


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
async def join_waitlist(job: JobModel) -> dict[str, Any]:
    runtime.get_node().join_waitlist(Job(job.name, job.ssh_password, job.requested_gpus, job.requested_run_time_hrs))
    return {
        "queued": True,
        "queue_length": len(runtime.get_node().waitlist()),
    }


class JobQueryModel(BaseModel):
    name: str
    ssh_password: str


@app.post("/leave_waitlist")
async def leave_waitlist(job_query: JobQueryModel) -> dict[str, bool]:
    return {"removed": runtime.get_node().leave_waitlist(job_query.name, job_query.ssh_password)}
