from time import time, sleep
from dataclasses import dataclass
from threading import Lock, Thread

from erbium.api import run_command_async
from erbium.api.os import GPUInfo, kill_all_sessions, run_command


@dataclass
class Job(object):
    name: str
    ssh_password: str
    requested_run_time_hrs: float
    start_time: float | None = None


class Node(object):
    def __init__(self, *, max_gpu_utilization: float = 10, max_gpu_memory_utilization: float = 10,
                 max_run_time_hrs: float = 168) -> None:
        """
        :param max_gpu_utilization: the maximum GPU utilization allowed to be considered available
        :param max_gpu_memory_utilization: the maximum GPU memory utilization allowed to be considered available
        :param max_run_time_hrs: the maximum run time in hours allowed for a job
        """
        self.max_gpu_utilization: float = max_gpu_utilization
        self.max_gpu_memory_utilization: float = max_gpu_memory_utilization
        self.max_run_time_hrs: float = max_run_time_hrs
        self._running_job: Job | None = None
        self._scheduled_jobs: list[Job] = []
        self._lock: Lock = Lock()
        self._thread: Thread = Thread(target=self._run, daemon=True, name="Node")
        self._thread.start()

    def _start_job(self, job: Job) -> None:
        run_command(f"echo \"access:{job.ssh_password}\" | chpasswd")
        job.start_time = time()
        self._running_job = job

    def _kill_running_job(self) -> None:
        kill_all_sessions("access", force=True)
        run_command_async("/workspace/venv/bin/jupyter lab --no-browser --port=8080 --ip=0.0.0.0 --ServerApp.root_dir=/workspace --ServerApp.trust_xheaders=True --ServerApp.allow_remote_access=True")
        self._running_job = None

    def _run(self) -> None:
        while True:
            with self._lock:
                if self._running_job and self._running_job.start_time + 3600 * self._running_job.requested_run_time_hrs < time():
                    self._kill_running_job()
                if not self._running_job and len(self._scheduled_jobs) > 0:
                    self._start_job(self._scheduled_jobs.pop(0))
                sleep(1)

    def running_job(self) -> tuple[str, float, float | None] | None:
        if not self._running_job:
            return None
        return self._running_job.name, self._running_job.requested_run_time_hrs, self._running_job.start_time

    def stop_running_job(self, ssh_password: str) -> bool:
        with self._lock:
            if self._running_job and self._running_job.ssh_password == ssh_password:
                self._kill_running_job()
                return True
        return False

    def join_waitlist(self, job: Job) -> None:
        with self._lock:
            self._scheduled_jobs.append(job)

    def leave_waitlist(self, job_name: str, ssh_password: str) -> bool:
        for job in self._scheduled_jobs:
            if job.name == job_name and job.ssh_password == ssh_password:
                with self._lock:
                    self._scheduled_jobs.remove(job)
                return True
        return False

    def waitlist(self) -> list[tuple[str, float]]:
        return [(job.name, job.requested_run_time_hrs) for job in self._scheduled_jobs]

    def wait_time_hrs(self) -> float:
        t = 0
        if self._running_job:
            t += self._running_job.start_time / 3600 + self._running_job.requested_run_time_hrs - time() / 3600
        for job in self._scheduled_jobs:
            t += job.requested_run_time_hrs
        return t

    def is_available(self, device: GPUInfo) -> bool:
        return device.utilization_percent < self.max_gpu_utilization and device.memory_utilization_percent < self.max_gpu_memory_utilization
