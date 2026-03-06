from dataclasses import dataclass
from json import load
from os import PathLike, makedirs
from os.path import exists
from threading import Lock

from erbium.api.docker import create_docker_compose, command_to_start_docker_compose
from erbium.api.os import run_command


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
    estimated_wait_time: float


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
        self._scheduled_containers: dict[str, Container] = {}
        self._gpu_occupancy: dict[int, set[str]] = {}
        self._lock: Lock = Lock()

    def _run_scheduled_container(self, name: str) -> None:
        profile_path = f"{self.docker_profile_dir}/{name}.yaml"
        if not exists(profile_path):
            raise ValueError(f"Docker profile {profile_path} not found")
        status = run_command(command_to_start_docker_compose(profile_path, name))
        if status.returncode != 0:
            raise RuntimeError(f"Failed to start container {name}: {status.stderr}")
        self._running_containers[name] = self._scheduled_containers.pop(name)

    def try_run_scheduled_container(self, name: str) -> bool:
        container = self._scheduled_containers.get(name)
        for gpu in container.job.requested_gpus:
            if not self.is_gpu_available(gpu):
                return False
        self._run_scheduled_container(name)
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
                wait_time = max(wait_time, max(
                    self._gpu_occupancy[gpu], key=lambda x: self._running_containers[x].job.requested_run_time_hrs
                ))
        # build container
        container = Container(container_name, output_dir, job)
        profile = create_docker_compose(
            container_name, input_dir=self.input_dir, output_dir=container.output_dir, gpus=tuple(job.requested_gpus)
        )
        with open(f"{self.docker_profile_dir}/{container_name}.yaml", "w") as f:
            f.write(profile)
        self._scheduled_containers[container_name] = container
        if wait_time < 0:
            self.try_run_scheduled_container(container_name)
        return ScheduledJob(job, job.requested_gpus, container, wait_time)

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

    def is_gpu_available(self, device_id: int) -> bool:
        return device_id not in self._gpu_occupancy or len(self._gpu_occupancy[device_id]) == 0
