from dataclasses import dataclass, asdict
from pathlib import Path
import re
from typing import Any
from subprocess import CalledProcessError, run
from time import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from erbium.api import Node, Job, get_all_gpu_info


@dataclass
class Runtime(object):
    homepage: str
    dashboard: str
    agent_dashboard: str
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
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

runtime: Runtime = Runtime("", "", "")

assets_dir = Path(__file__).with_name("assets")
runtime.homepage = (assets_dir / "index.html").read_text()
runtime.dashboard = (assets_dir / "dash.html").read_text()
runtime.agent_dashboard = (assets_dir / "agent.html").read_text()

AGENTS: dict[str, str] = {
    "codex": "Codex",
    "claude": "Claude Code",
}
MAX_AGENT_OUTPUT_CHARS = 16_000
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


@dataclass
class AgentRuntimeStatus:
    agent: str
    display_name: str
    state: str = "idle"
    task: str = ""
    latest_output: str = ""
    exit_code: int | None = None
    started_at: float | None = None
    updated_at: float | None = None
    finished_at: float | None = None


agent_statuses: dict[str, AgentRuntimeStatus] = {
    agent: AgentRuntimeStatus(agent=agent, display_name=display_name)
    for agent, display_name in AGENTS.items()
}


def _clean_agent_output(output: str) -> str:
    output = ANSI_ESCAPE_RE.sub("", output)
    output = output.replace("\r", "\n")
    output = CONTROL_CHAR_RE.sub("", output)
    return output[-MAX_AGENT_OUTPUT_CHARS:]


def _get_agent_status(agent: str) -> AgentRuntimeStatus:
    status = agent_statuses.get(agent.lower())
    if not status:
        raise HTTPException(status_code=404, detail="Unknown agent.")
    return status


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return runtime.homepage


@app.get("/dash", response_class=HTMLResponse)
async def dash() -> str:
    return runtime.dashboard


@app.get("/codex", response_class=HTMLResponse)
async def codex_dashboard() -> str:
    return runtime.agent_dashboard


@app.get("/claude", response_class=HTMLResponse)
async def claude_dashboard() -> str:
    return runtime.agent_dashboard


@app.get("/waitlist")
async def waitlist() -> dict[str, Any]:
    return {
        "wait_time_hrs": runtime.get_node().wait_time_hrs(), "running_job": runtime.get_node().running_job(),
        "jobs": runtime.get_node().waitlist()
    }


@app.get("/availability")
async def availability() -> dict[str, Any]:
    return {info.name: {
        "available": runtime.get_node().is_available(info), **asdict(info)
    } for device_id, info in get_all_gpu_info().items()}


class JobModel(BaseModel):
    name: str
    ssh_password: str
    requested_run_time_hrs: float


@app.post("/join_waitlist")
async def join_waitlist(job: JobModel) -> dict[str, Any]:
    runtime.get_node().join_waitlist(Job(job.name, job.ssh_password, job.requested_run_time_hrs))
    return {
        "queued": True,
        "queue_length": len(runtime.get_node().waitlist()),
    }


class RunningJobModel(BaseModel):
    ssh_password: str


@app.post("/stop_running_job")
async def stop_running_job(job: RunningJobModel) -> dict[str, bool]:
    return {"stopped": runtime.get_node().stop_running_job(job.ssh_password)}


class JobQueryModel(RunningJobModel):
    name: str


@app.post("/leave_waitlist")
async def leave_waitlist(job_query: JobQueryModel) -> dict[str, bool]:
    return {"removed": runtime.get_node().leave_waitlist(job_query.name, job_query.ssh_password)}


class AptInstallPackages(BaseModel):
    packages: list[str]


class AgentStatusUpdate(BaseModel):
    state: str
    task: str | None = None
    output_chunk: str | None = None
    exit_code: int | None = None


@app.get("/agent_status")
async def get_agent_statuses() -> dict[str, Any]:
    return {agent: asdict(status) for agent, status in agent_statuses.items()}


@app.get("/agent_status/{agent}")
async def get_agent_status(agent: str) -> dict[str, Any]:
    return asdict(_get_agent_status(agent))


@app.post("/agent_status/{agent}")
async def update_agent_status(agent: str, update: AgentStatusUpdate) -> dict[str, Any]:
    status = _get_agent_status(agent)
    now = time()
    state = update.state.strip().lower()
    if state not in {"started", "running", "finished", "failed", "idle"}:
        raise HTTPException(status_code=400, detail="Invalid agent state.")

    if state == "started":
        status.state = "running"
        status.latest_output = ""
        status.exit_code = None
        status.started_at = now
        status.finished_at = None
    elif state == "finished":
        status.state = "finished" if update.exit_code in (None, 0) else "failed"
        status.finished_at = now
        status.exit_code = update.exit_code
    else:
        status.state = state
        if update.exit_code is not None:
            status.exit_code = update.exit_code

    if update.task is not None:
        status.task = update.task[-512:]
    if update.output_chunk is not None:
        status.latest_output = _clean_agent_output(update.output_chunk)
    status.updated_at = now

    return asdict(status)


@app.post("/apt_install")
async def apt_install(packages: AptInstallPackages) -> dict[str, Any]:
    package_names = [package.strip() for package in packages.packages if package.strip()]
    if not package_names:
        raise HTTPException(status_code=400, detail="At least one package is required.")

    try:
        run(("apt", "install", "-y", *package_names), check=True)
    except CalledProcessError as error:
        raise HTTPException(status_code=500, detail="apt install failed.") from error

    return {"installed": package_names}
