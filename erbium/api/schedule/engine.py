from dataclasses import dataclass
from json import load
from os import PathLike, makedirs
from os.path import exists
from threading import Lock
from time import time

from erbium.api.docker import create_docker_compose, command_to_start_docker_compose
from erbium.api.os import run_command, get_gpu_names_and_specs, GPUInfo


@dataclass
class Job(object):
    name: str
    requested_gpus: set[int]
    requested_run_time_hrs: float


@dataclass
class Container(object):
    name: str
    output_dir: str
    job: Job


@dataclass
class ScheduledJob(object):
    job: Job
    allocated_gpus: set[int]
    assigned_container: Container
    estimated_time_to_run: float


class Scheduler(object):
    def __init__(self, root_dir: str | PathLike[str], input_dir: str | PathLike[str], *,
                 max_gpu_utilization: float = .1, max_run_time_hrs: float = 168) -> None:
        """
        :param max_gpu_utilization: the maximum GPU utilization allowed to be considered available
        :param max_run_time_hrs: the maximum run time in hours allowed for a job
        """
        self.root_dir: str = str(root_dir)
        self.input_dir: str = str(input_dir)
        self.docker_profile_dir: str = f"{self.root_dir}/docker-profiles"
        makedirs(self.docker_profile_dir, exist_ok=True)
        self.max_gpu_utilization: float = max_gpu_utilization
        self.max_run_time_hrs: float = max_run_time_hrs
        self._running_containers: dict[str, Container] = {}
        self._scheduled_jobs: dict[str, ScheduledJob] = {}
        self._gpu_names_and_specs: dict[int, GPUInfo] = get_gpu_names_and_specs()
        self._gpu_occupancy: dict[int, set[str]] = {}
        self._lock: Lock = Lock()

    def check_scheduled_jobs(self, *, try_running: bool = True) -> int:
        r = 0
        for job in self._scheduled_jobs.values():
            if job.estimated_time_to_run < time():
                r += 1
                if try_running:
                    self.try_run_scheduled_job(job.assigned_container.name)
        return r

    def _run_scheduled_job(self, name: str) -> None:
        profile_path = f"{self.docker_profile_dir}/{name}.yaml"
        if not exists(profile_path):
            raise ValueError(f"Docker profile {profile_path} not found")
        status = run_command(command_to_start_docker_compose(profile_path, name))
        if status.returncode != 0:
            raise RuntimeError(f"Failed to start container {name}: {status.stderr}")
        self._running_containers[name] = self._scheduled_jobs.pop(name).assigned_container

    def try_run_scheduled_job(self, name: str) -> bool:
        container = self._scheduled_jobs.get(name)
        for gpu in container.job.requested_gpus:
            if not self.is_gpu_available(gpu):
                return False
        self._run_scheduled_job(name)
        return True

    def schedule(self, job: Job) -> ScheduledJob:
        with self._lock:
            return self._schedule(job)

    def _schedule(self, job: Job) -> ScheduledJob:
        # check for hard requirements
        if job.requested_run_time_hrs > self.max_run_time_hrs:
            raise ValueError(
                f"Requested run time {job.requested_run_time_hrs} exceeds maximum of {self.max_run_time_hrs} hours"
            )
        container_name = self.suggest_container_name(job)
        if container_name in self._running_containers:
            raise ValueError(f"Container with name {container_name} already exists")
        # create output dir
        output_dir = f"{self.root_dir}/erbium_output-{container_name}"
        makedirs(output_dir)
        # check for GPU availability
        self.gather_utilization_data()
        wait_time = -1
        for gpu in job.requested_gpus:
            if gpu in self._gpu_occupancy:
                wait_time = max(wait_time, self._running_containers[max(
                    self._gpu_occupancy[gpu], key=lambda x: self._running_containers[x].job.requested_run_time_hrs
                )].job.requested_run_time_hrs * 3600)
        # build container
        container = Container(container_name, output_dir, job)
        profile = create_docker_compose(
            container_name, input_dir=self.input_dir, output_dir=container.output_dir, gpus=tuple(job.requested_gpus)
        )
        with open(f"{self.docker_profile_dir}/{container_name}.yaml", "w") as f:
            f.write(profile)
        r = self._scheduled_jobs[container_name] = ScheduledJob(job, job.requested_gpus, container, time() + wait_time)
        if wait_time < 0:
            self.try_run_scheduled_job(container_name)
        return r

    def suggest_container_name(self, job: Job) -> str:
        return f"{job.name}-{len(self._running_containers) + 1}"

    def gather_utilization_data(self) -> None:
        for container in self._running_containers.values():
            with open(f"{container.output_dir}/gpu_max_utilization.json") as f:
                data = load(f)
                for gpu in data["gpus"]:
                    gpu_id, util, mem_util = (
                        gpu["index"], gpu["max_gpu_util_percent"], gpu["max_memory_util_percent"]
                    )
                    if util > self.max_gpu_utilization or mem_util > self.max_gpu_utilization:
                        if gpu_id not in self._gpu_occupancy:
                            self._gpu_occupancy[gpu_id] = set()
                        self._gpu_occupancy[gpu_id].add(container.name)
                    elif gpu_id in self._gpu_occupancy and container.name in self._gpu_occupancy[gpu_id]:
                        self._gpu_occupancy[gpu_id].remove(container.name)

    def list_gpus(self) -> dict[int, GPUInfo]:
        r = self._gpu_names_and_specs.copy()
        for gpu_id, gpu_info in r.items():
            gpu_info.occupied_by = self._gpu_occupancy.get(gpu_id, set())
        return r

    def is_gpu_available(self, device_id: int) -> bool:
        return len(self._gpu_occupancy.get(device_id, set())) == 0

    @property
    def running_containers(self) -> dict[str, Container]:
        return self._running_containers.copy()

    @property
    def scheduled_jobs(self) -> dict[str, ScheduledJob]:
        return self._scheduled_jobs.copy()
