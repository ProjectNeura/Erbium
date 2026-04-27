from collections import defaultdict
from dataclasses import dataclass
from json import loads
from platform import processor, system
from subprocess import run

from psutil import virtual_memory, cpu_percent, cpu_freq, cpu_count


@dataclass
class CPUInfo(object):
    device_id: int
    name: str
    utilization_percent: float
    memory_utilization_percent: float
    clock_speed_mhz: float | None
    memory_clock_speed_mhz: float | None
    total_memory_gb: float
    physical_cores: int
    logical_cores: int


def _get_total_memory_gb() -> float:
    return virtual_memory().total / 1073741824


def _get_memory_utilization_percent() -> float:
    return virtual_memory().percent


def _avg_cpu_percent(cpu_ids: list[int]) -> float:
    per_cpu = cpu_percent(interval=None, percpu=True)
    selected = [per_cpu[i] for i in cpu_ids if 0 <= i < len(per_cpu)]
    if not selected:
        return cpu_percent(interval=None)
    return sum(selected) / len(selected)


def _avg_clock_mhz(cpu_ids: list[int]) -> float | None:
    try:
        freqs = cpu_freq(percpu=True)
        if freqs:
            selected = [freqs[i].current for i in cpu_ids if 0 <= i < len(freqs)]
            if selected:
                return sum(selected) / len(selected)
        freq = cpu_freq()
        return None if freq is None else freq.current
    except Exception:
        return None


def _get_single_cpu_fallback() -> dict[int, dict]:
    logical_count = cpu_count(logical=True) or 1
    physical_count = cpu_count(logical=False) or logical_count
    return {0: {
        "name": processor() or "CPU", "logical_cpus": list(range(logical_count)),
        "physical_cores": physical_count, "logical_cores": logical_count
    }}


def _get_linux_cpu_sockets() -> dict[int, dict]:
    sockets: dict[int, dict] = defaultdict(
        lambda: {
            "name": "CPU",
            "logical_cpus": [],
            "core_ids": set(),
        }
    )
    current: dict[str, str] = {}

    def flush_cpu(cpu: dict[str, str]) -> None:
        if not cpu:
            return
        processor = int(cpu.get("processor", 0))
        socket_id = int(cpu.get("physical id", 0))
        core_id = cpu.get("core id")
        model_name = cpu.get("model name") or cpu.get("Hardware") or "CPU"
        sockets[socket_id]["logical_cpus"].append(processor)
        sockets[socket_id]["name"] = model_name
        if core_id is not None:
            sockets[socket_id]["core_ids"].add(core_id)

    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    flush_cpu(current)
                    current = {}
                    continue
                if ":" in line:
                    key, value = line.split(":", 1)
                    current[key.strip()] = value.strip()
        flush_cpu(current)
    except Exception:
        return _get_single_cpu_fallback()
    result: dict[int, dict] = {}
    for socket_id, info in sockets.items():
        logical_cpus = sorted(info["logical_cpus"])
        logical_cores = len(logical_cpus)
        physical_cores = len(info["core_ids"]) or logical_cores
        result[socket_id] = {
            "name": info["name"],
            "logical_cpus": logical_cpus,
            "physical_cores": physical_cores,
            "logical_cores": logical_cores,
        }
    return result or _get_single_cpu_fallback()


def _run_powershell_json(command: str) -> object | None:
    try:
        completed = run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                command,
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if completed.returncode != 0:
            return None
        stdout = completed.stdout.strip()
        if not stdout:
            return None
        return loads(stdout)
    except Exception:
        return None


def _get_windows_cpu_sockets() -> dict[int, dict]:
    """
    Windows exposes CPU package info through Win32_Processor.

    Caveat:
    psutil does not reliably expose which logical CPU belongs to which socket
    on Windows, so utilization is split evenly across sockets as an approximation.
    For most monitoring dashboards, this is good enough.
    """
    command = """
    Get-CimInstance Win32_Processor |
    Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed |
    ConvertTo-Json
    """
    data = _run_powershell_json(command)
    if data is None:
        return _get_single_cpu_fallback()
    if isinstance(data, dict):
        cpus = [data]
    else:
        cpus = data
    if not cpus:
        return _get_single_cpu_fallback()
    total_logical = cpu_count(logical=True) or sum(
        int(cpu.get("NumberOfLogicalProcessors", 0) or 0) for cpu in cpus
    )
    result: dict[int, dict] = {}
    start = 0
    for socket_id, cpu in enumerate(cpus):
        logical_cores = int(cpu.get("NumberOfLogicalProcessors", 0) or 0)
        physical_cores = int(cpu.get("NumberOfCores", 0) or logical_cores or 1)
        if logical_cores <= 0:
            logical_cores = max(1, total_logical // len(cpus))
        end = min(start + logical_cores, total_logical)
        logical_cpus = list(range(start, end))
        start = end
        result[socket_id] = {
            "name": cpu.get("Name") or processor() or "CPU",
            "logical_cpus": logical_cpus,
            "physical_cores": physical_cores,
            "logical_cores": logical_cores,
        }
    return result or _get_single_cpu_fallback()


def _get_cpu_sockets() -> dict[int, dict]:
    system_name = system().lower()
    if system_name == "linux":
        return _get_linux_cpu_sockets()
    if system_name == "windows":
        return _get_windows_cpu_sockets()
    return _get_single_cpu_fallback()


def get_all_cpu_info() -> dict[int, CPUInfo]:
    sockets = _get_cpu_sockets()
    memory_utilization_percent = _get_memory_utilization_percent()
    total_memory_gb = _get_total_memory_gb()
    result: dict[int, CPUInfo] = {}
    for socket_id, info in sorted(sockets.items()):
        logical_cpus = info["logical_cpus"]
        result[socket_id] = CPUInfo(
            device_id=socket_id,
            name=info["name"],
            utilization_percent=_avg_cpu_percent(logical_cpus),
            memory_utilization_percent=memory_utilization_percent,
            clock_speed_mhz=_avg_clock_mhz(logical_cpus),
            memory_clock_speed_mhz=None,
            total_memory_gb=total_memory_gb,
            physical_cores=info["physical_cores"],
            logical_cores=info["logical_cores"],
        )
    return result
