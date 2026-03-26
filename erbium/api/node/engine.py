from time import time
from dataclasses import dataclass
from threading import Lock, Thread

from erbium.api.os import get_all_gpu_info, GPUInfo, kill_all_sessions, run_command


@dataclass
class Job(object):
    name: str
    ssh_password: str
    requested_gpus: set[int]
    requested_run_time_hrs: float
    start_time: float | None = None


class Node(object):
    def __init__(self, *, max_gpu_utilization: float = .1, max_gpu_memory_utilization: float = .1,
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

    def _run(self) -> None:
        while True:
            if self._running_job and self._running_job.start_time + 3600 * self._running_job.requested_run_time_hrs < time():
                kill_all_sessions("access", force=True)
                self._running_job = None
            if not self._running_job:
                self._start_job(self._scheduled_jobs.pop(0))

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
