from typing import Any, Callable, Sequence
from os import PathLike
from os.path import exists, abspath


__DOCKER_DIR__: str = f"{abspath(__file__)[:-28]}docker".replace("\\", "/")
__DEFAULT_BASE_CONTAINER__: str = "nvidia/cuda:13.0.0-devel-ubuntu24.04"
__DEFAULT_HOSTNAME__: str = "erbium"
__DEFAULT_CONTAINER_NAME__: str = "erbium"
__DEFAULT_SHARED_NETWORK__: str = "labnet"
__DEFAULT_SSH_PASSWORD__: str = "sshpassword"
__DEFAULT_INPUT_DIR__: str = "S:/erbium_input"
__DEFAULT_OUTPUT_DIR__: str = "S:/erbium_output"
__DEFAULT_GPU_DRIVER__: str = "nvidia"
__DEFAULT_GPUS__: str = "all"


def _set_gpus(gpus: int | str | Sequence[int]) -> str:
    if isinstance(gpus, (int, str)):
        return f"count: {gpus}"
    return f"device_ids: {list(map(str, gpus))}"


__TERMS_TO_BE_REPLACED__: dict[str, tuple[str, Callable[[Any], str]]] = {
    "service_name": ("SERVICE_NAME", lambda x: x),
    "base_container": (f"image: {__DEFAULT_BASE_CONTAINER__}", lambda x: f"image: {x}"),
    "hostname": (f"hostname: {__DEFAULT_HOSTNAME__}", lambda x: f"hostname: {x}"),
    "container_name": (f"container_name: {__DEFAULT_CONTAINER_NAME__}", lambda x: f"container_name: {x}"),
    "shared_network": (__DEFAULT_SHARED_NETWORK__, lambda x: x),
    "ssh_password": (f"root:{__DEFAULT_SSH_PASSWORD__}", lambda x: f"root:{x}"),
    "input_dir": (f"- {__DEFAULT_INPUT_DIR__}:", lambda x: f"- {x}:"),
    "output_dir": (f"- {__DEFAULT_OUTPUT_DIR__}:", lambda x: f"- {x}:"),
    "gpu_driver": (f"- driver: {__DEFAULT_GPU_DRIVER__}", lambda x: f"- driver: {x}"),
    "gpus": (f"count: {__DEFAULT_GPUS__}", _set_gpus)
}


def create_docker_compose(service_name: str, *, base_container: str = __DEFAULT_BASE_CONTAINER__,
                          hostname: str = __DEFAULT_HOSTNAME__, container_name: str = __DEFAULT_CONTAINER_NAME__,
                          shared_network: str = __DEFAULT_SHARED_NETWORK__,
                          input_dir: str | PathLike[str] = __DEFAULT_INPUT_DIR__,
                          output_dir: str | PathLike[str] = __DEFAULT_OUTPUT_DIR__,
                          gpu_driver: str = __DEFAULT_GPU_DRIVER__,
                          gpus: int | str | Sequence[int] = __DEFAULT_GPUS__) -> str:
    """
    We believe you are able to understand what these parameters are for by reading the "docker-compose.yaml" file, so
    we won't go into detail here.
    :return: the content of the generated Docker-compose file
    """
    template_path = f"{__DOCKER_DIR__}/docker-compose.yaml"
    if not exists(template_path):
        raise FileNotFoundError(f"Docker Compose template {template_path} not found, check your installtion")
    with open(template_path) as f:
        template = f.read()
    for term, (original, replacement) in __TERMS_TO_BE_REPLACED__.items():
        template = template.replace(original, replacement(locals()[term]))
    template = template.replace("./", f"{__DOCKER_DIR__}/")
    return template


def command_to_start_docker_compose(profile_path: str | PathLike[str], service_name: str, *,
                                    force_build: bool = True) -> str:
    """
    Start the Docker-compose service.
    :param profile_path: the path to the Docker-compose file
    :param service_name: the name of the service to start
    :param force_build: whether to force rebuild the service
    :return: the command to run
    """
    cmd = f"docker compose -f {profile_path} up -d {service_name}"
    if force_build:
        cmd += " --build"
    return cmd
