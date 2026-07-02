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
from erbium.server.availability import availability_payload


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
MAX_AGENT_SESSIONS = 30
AGENT_RUNNING_STALE_SECONDS = 15
AGENT_RUNNING_IDLE_SECONDS = 20
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
SURROGATE_RE = re.compile(r"[\ud800-\udfff]")
SESSION_ID_RE = re.compile(r"[^A-Za-z0-9_.:-]")
TERMINAL_ROWS = 120
TERMINAL_COLS = 160


@dataclass
class AgentSessionStatus:
    agent: str
    display_name: str
    session_id: str
    state: str = "idle"
    task: str = ""
    latest_output: str = ""
    exit_code: int | None = None
    started_at: float | None = None
    updated_at: float | None = None
    output_updated_at: float | None = None
    finished_at: float | None = None


agent_sessions: dict[str, dict[str, AgentSessionStatus]] = {agent: {} for agent in AGENTS}


def _terminal_param_values(params: str) -> list[int]:
    values: list[int] = []
    for value in params.replace("?", "").split(";"):
        if not value:
            values.append(0)
            continue
        try:
            values.append(int(value.split(":", 1)[0]))
        except ValueError:
            values.append(0)
    return values


def _json_safe_text(value: str) -> str:
    value = SURROGATE_RE.sub("\ufffd", value)
    return value.encode("utf-8", "replace").decode("utf-8")


def _render_terminal_output(output: str) -> str:
    output = _json_safe_text(output)
    screen: list[list[str]] = [[" "] * TERMINAL_COLS]
    row = 0
    col = 0
    index = 0

    def ensure_row(target: int) -> None:
        nonlocal row
        while len(screen) <= target:
            screen.append([" "] * TERMINAL_COLS)
        if len(screen) > TERMINAL_ROWS:
            overflow = len(screen) - TERMINAL_ROWS
            del screen[:overflow]
            row = max(0, row - overflow)

    def clear_line(target_row: int, start: int = 0, end: int = TERMINAL_COLS) -> None:
        ensure_row(target_row)
        for pos in range(max(0, start), min(TERMINAL_COLS, end)):
            screen[target_row][pos] = " "

    def skip_until_terminator(start: int, terminators: tuple[str, ...]) -> int:
        pos = start
        while pos < len(output):
            if output[pos] in terminators:
                return pos + 1
            if output[pos] == "\x1b" and pos + 1 < len(output) and output[pos + 1] == "\\":
                return pos + 2
            pos += 1
        return len(output)

    def handle_csi(params: str, final: str) -> None:
        nonlocal row, col, screen
        values = _terminal_param_values(params)
        first = values[0] if values else 0
        amount = first or 1

        if final in {"H", "f"}:
            row = max(0, (values[0] if len(values) >= 1 and values[0] else 1) - 1)
            col = max(0, (values[1] if len(values) >= 2 and values[1] else 1) - 1)
            ensure_row(row)
            col = min(col, TERMINAL_COLS - 1)
        elif final == "A":
            row = max(0, row - amount)
        elif final == "B":
            row += amount
            ensure_row(row)
        elif final == "C":
            col = min(TERMINAL_COLS - 1, col + amount)
        elif final == "D":
            col = max(0, col - amount)
        elif final == "G":
            col = min(TERMINAL_COLS - 1, max(0, amount - 1))
        elif final == "J":
            if first in {0, 2, 3}:
                screen = [[" "] * TERMINAL_COLS]
                row = 0
                col = 0
        elif final == "K":
            if first == 1:
                clear_line(row, 0, col + 1)
            elif first == 2:
                clear_line(row)
            else:
                clear_line(row, col)

    while index < len(output):
        char = output[index]

        if char == "\x1b":
            if index + 1 >= len(output):
                break
            introducer = output[index + 1]
            if introducer == "[":
                match = re.match(r"\x1b\[([0-?]*[ -/]*)?([@-~])", output[index:])
                if match:
                    handle_csi(match.group(1) or "", match.group(2))
                    index += len(match.group(0))
                    continue
            if introducer in {"]", "P", "_", "^"}:
                index = skip_until_terminator(index + 2, ("\x07",))
                continue
            index += 2
            continue

        if char == "\x9b":
            match = re.match(r"\x9b([0-?]*[ -/]*)?([@-~])", output[index:])
            if match:
                handle_csi(match.group(1) or "", match.group(2))
                index += len(match.group(0))
                continue
        if char in {"\x90", "\x9d", "\x9e", "\x9f"}:
            index = skip_until_terminator(index + 1, ("\x07", "\x9c"))
            continue

        if char == "\r":
            col = 0
        elif char == "\n":
            row += 1
            col = 0
            ensure_row(row)
        elif char == "\b":
            col = max(0, col - 1)
        elif char == "\t":
            col = min(TERMINAL_COLS - 1, col + (8 - (col % 8)))
        elif CONTROL_CHAR_RE.match(char):
            pass
        else:
            ensure_row(row)
            screen[row][col] = char
            col += 1
            if col >= TERMINAL_COLS:
                col = 0
                row += 1
                ensure_row(row)
        index += 1

    lines = ["".join(line).rstrip() for line in screen]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)[-MAX_AGENT_OUTPUT_CHARS:]


def _clean_agent_output(output: str) -> str:
    output = _render_terminal_output(output)
    output = re.sub(r"\[[?0-9;: ]*[A-Za-z]", "", output)
    output = "\n".join(line for line in output.splitlines() if not re.search(r"][0-9;?]*;", line))
    return _json_safe_text(output[-MAX_AGENT_OUTPUT_CHARS:])


def _get_agent_name(agent: str) -> str:
    agent = agent.lower()
    if agent not in AGENTS:
        raise HTTPException(status_code=404, detail="Unknown agent.")
    return agent


def _normalize_session_id(session_id: str) -> str:
    session_id = SESSION_ID_RE.sub("-", session_id.strip())[:128]
    if not session_id:
        raise HTTPException(status_code=400, detail="Session id is required.")
    return session_id


def _session_sort_key(status: AgentSessionStatus) -> float:
    return status.updated_at or status.started_at or status.finished_at or 0


def _sorted_sessions(agent: str) -> list[AgentSessionStatus]:
    return sorted(agent_sessions[agent].values(), key=_session_sort_key, reverse=True)


def _is_stale_running_session(status: AgentSessionStatus, now: float) -> bool:
    if status.state != "running":
        return False
    if status.updated_at is None:
        return True
    return now - status.updated_at > AGENT_RUNNING_STALE_SECONDS


def _is_idle_running_session(status: AgentSessionStatus, now: float) -> bool:
    if status.state != "running" or _is_stale_running_session(status, now):
        return False
    last_change = status.output_updated_at or status.started_at
    if last_change is None:
        return False
    return now - last_change > AGENT_RUNNING_IDLE_SECONDS


def _session_payload(status: AgentSessionStatus, now: float | None = None) -> dict[str, Any]:
    now = time() if now is None else now
    payload = asdict(status)
    payload["task"] = _json_safe_text(payload["task"])
    payload["latest_output"] = _json_safe_text(payload["latest_output"])
    payload["raw_state"] = status.state
    payload["stale"] = _is_stale_running_session(status, now)
    payload["idle"] = _is_idle_running_session(status, now)
    if payload["stale"]:
        payload["state"] = "stale"
    elif payload["idle"]:
        payload["state"] = "idle"
    return payload


def _agent_payload(agent: str) -> dict[str, Any]:
    now = time()
    sessions = _sorted_sessions(agent)
    session_payloads = [_session_payload(session, now) for session in sessions]
    return {
        "agent": agent,
        "display_name": AGENTS[agent],
        "active_count": sum(1 for session in session_payloads if session["state"] == "running"),
        "sessions": session_payloads,
        "latest_session": session_payloads[0] if session_payloads else None,
    }


def _get_or_create_session(agent: str, session_id: str) -> AgentSessionStatus:
    session_id = _normalize_session_id(session_id)
    sessions = agent_sessions[agent]
    if session_id not in sessions:
        sessions[session_id] = AgentSessionStatus(
            agent=agent,
            display_name=AGENTS[agent],
            session_id=session_id,
        )
    return sessions[session_id]


def _get_session(agent: str, session_id: str) -> AgentSessionStatus:
    session_id = _normalize_session_id(session_id)
    status = agent_sessions[agent].get(session_id)
    if not status:
        raise HTTPException(status_code=404, detail="Unknown agent session.")
    return status


def _prune_agent_sessions(agent: str) -> None:
    sessions = _sorted_sessions(agent)
    if len(sessions) <= MAX_AGENT_SESSIONS:
        return

    keep = {session.session_id for session in sessions[:MAX_AGENT_SESSIONS] if session.state == "running"}
    keep.update(session.session_id for session in sessions[:MAX_AGENT_SESSIONS - len(keep)])
    for session in sessions:
        if session.session_id not in keep and session.state != "running":
            agent_sessions[agent].pop(session.session_id, None)


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
    return availability_payload(runtime.get_node(), get_all_gpu_info())


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
    session_id: str | None = None
    task: str | None = None
    output_chunk: str | None = None
    exit_code: int | None = None


@app.get("/agent_status")
async def get_agent_statuses() -> dict[str, Any]:
    return {agent: _agent_payload(agent) for agent in AGENTS}


@app.get("/agent_status/{agent}")
async def get_agent_status(agent: str) -> dict[str, Any]:
    return _agent_payload(_get_agent_name(agent))


@app.post("/agent_status/{agent}")
async def update_agent_status(agent: str, update: AgentStatusUpdate) -> dict[str, Any]:
    agent = _get_agent_name(agent)
    session_id = update.session_id or "default"
    return _update_agent_session(agent, session_id, update)


@app.get("/agent_status/{agent}/{session_id}")
async def get_agent_session_status(agent: str, session_id: str) -> dict[str, Any]:
    agent = _get_agent_name(agent)
    return _session_payload(_get_session(agent, session_id))


@app.post("/agent_status/{agent}/{session_id}")
async def update_agent_session_status(agent: str, session_id: str, update: AgentStatusUpdate) -> dict[str, Any]:
    agent = _get_agent_name(agent)
    return _update_agent_session(agent, session_id, update)


def _update_agent_session(agent: str, session_id: str, update: AgentStatusUpdate) -> dict[str, Any]:
    status = _get_or_create_session(agent, session_id)
    now = time()
    state = update.state.strip().lower()
    if state not in {"started", "running", "finished", "failed", "idle"}:
        raise HTTPException(status_code=400, detail="Invalid agent state.")

    def update_output(output_chunk: str) -> None:
        cleaned_output = _clean_agent_output(output_chunk)
        if cleaned_output != status.latest_output:
            status.latest_output = cleaned_output
            status.output_updated_at = now

    is_terminal = status.state in {"finished", "failed"}
    if is_terminal and state in {"running", "idle"}:
        if update.task is not None:
            status.task = _json_safe_text(update.task[-512:])
        if update.output_chunk is not None:
            update_output(update.output_chunk)
        status.updated_at = now
        _prune_agent_sessions(agent)
        return _session_payload(status, now)

    if state == "started":
        status.state = "running"
        status.latest_output = ""
        status.output_updated_at = now
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
        status.task = _json_safe_text(update.task[-512:])
    if update.output_chunk is not None:
        update_output(update.output_chunk)
    status.updated_at = now
    _prune_agent_sessions(agent)

    return _session_payload(status, now)


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
