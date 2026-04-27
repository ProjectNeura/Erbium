from time import time, sleep
from dataclasses import dataclass
from threading import Lock, Thread

from erbium.api.os import GPUInfo, kill_all_sessions, run_command


@dataclass
class Job(object):
    name: str
    ssh_password: str
    requested_run_time_hrs: float
    start_time: float | None = None


class Node(object):
    JUPYTER_LAB_COMMAND = (
        "su - access -c "
        "\"nohup /workspace/venv/bin/jupyter lab --no-browser --port=8080 --ip=0.0.0.0 "
        "--ServerApp.root_dir=/workspace --ServerApp.trust_xheaders=True "
        "--ServerApp.allow_remote_access=True >/tmp/jupyter-lab.log 2>&1 &\""
    )

    def __init__(self, *, max_gpu_utilization: float = 15, max_gpu_memory_utilization: float = 15,
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
        self._transitioning: bool = False
        self._thread: Thread = Thread(target=self._run, daemon=True, name="Node")
        self._thread.start()

    @staticmethod
    def _start_job(job: Job) -> None:
        run_command(f"echo \"access:{job.ssh_password}\" | chpasswd")

    def _mark_job_started(self, job: Job) -> None:
        with self._lock:
            job.start_time = time()
            self._running_job = job
            self._transitioning = False

    @staticmethod
    def _kill_running_job() -> None:
        kill_all_sessions("access", force=True)

    @classmethod
    def _restart_jupyter_lab(cls) -> None:
        run_command(cls.JUPYTER_LAB_COMMAND)

    def _mark_job_stopped(self) -> None:
        with self._lock:
            self._transitioning = False

    def _run(self) -> None:
        while True:
            job_to_kill = False
            job_to_start: Job | None = None
            with self._lock:
                if (
                    self._running_job
                    and self._running_job.start_time + 3600 * self._running_job.requested_run_time_hrs < time()
                    and not self._transitioning
                ):
                    self._running_job = None
                    self._transitioning = True
                    job_to_kill = True
                if not self._running_job and self._scheduled_jobs and not self._transitioning:
                    job_to_start = self._scheduled_jobs.pop(0)
                    self._transitioning = True
            if job_to_kill:
                self._kill_running_job()
                self._restart_jupyter_lab()
                self._mark_job_stopped()
            if job_to_start:
                self._start_job(job_to_start)
                self._mark_job_started(job_to_start)
            sleep(1)

    def running_job(self) -> tuple[str, float, float | None] | None:
        if not self._running_job:
            return None
        return self._running_job.name, self._running_job.requested_run_time_hrs, self._running_job.start_time

    def stop_running_job(self, ssh_password: str) -> bool:
        should_stop = False
        with self._lock:
            if (
                self._running_job
                and self._running_job.ssh_password == ssh_password
                and not self._transitioning
            ):
                self._running_job = None
                self._transitioning = True
                should_stop = True
        if not should_stop:
            return False
        self._kill_running_job()
        self._restart_jupyter_lab()
        self._mark_job_stopped()
        return True

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
