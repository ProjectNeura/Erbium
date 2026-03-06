from typing import Callable
from os import PathLike
from os.path import exists, abspath


__DOCKER_DIR__: str = f"{abspath(__file__)[:-28]}docker"
__DEFAULT_BASE_CONTAINER__: str = "nvidia/cuda:13.0.0-devel-ubuntu24.04"
__DEFAULT_HOSTNAME__: str = "erbium"
__DEFAULT_CONTAINER_NAME__: str = "erbium"
__DEFAULT_INPUT_DIR__: str = "S:/erbium_input"
__DEFAULT_OUTPUT_DIR__: str = "S:/erbium_output"
__DEFAULT_GPU_DRIVER__: str = "nvidia"
__DEFAULT_GPU_COUNT__: str = "all"

__TERMS_TO_BE_REPLACED__: dict[str, tuple[str, Callable[[str], str]]] = {
    "service_name": ("SERVICE_NAME", lambda x: x),
    "base_container": (f"image: {__DEFAULT_BASE_CONTAINER__}", lambda x: f"image: {x}"),
    "hostname": (f"hostname: {__DEFAULT_HOSTNAME__}", lambda x: f"hostname: {x}"),
    "container_name": (f"container_name: {__DEFAULT_CONTAINER_NAME__}", lambda x: f"container_name: {x}"),
    "input_dir": (f"- {__DEFAULT_INPUT_DIR__}:", lambda x: f"- {x}:"),
    "output_dir": (f"- {__DEFAULT_OUTPUT_DIR__}:", lambda x: f"- {x}:"),
    "gpu_driver": (f"- driver: {__DEFAULT_GPU_DRIVER__}", lambda x: f"- driver: {x}"),
    "gpu_count": (f"count: {__DEFAULT_GPU_COUNT__}", lambda x: f"count: {x}")
}


def create_docker_compose(service_name: str, *, base_container: str = __DEFAULT_BASE_CONTAINER__,
                          hostname: str = __DEFAULT_HOSTNAME__, container_name: str = __DEFAULT_CONTAINER_NAME__,
                          input_dir: str | PathLike[str] = __DEFAULT_INPUT_DIR__,
                          output_dir: str | PathLike[str] = __DEFAULT_OUTPUT_DIR__,
                          gpu_driver: str = __DEFAULT_GPU_DRIVER__, gpu_count: str = __DEFAULT_GPU_COUNT__) -> str:
    """
    We believe you are able to understand what these parameters are for by reading the "docker-compose.yaml" file, so
    we won't go into detail here.
    :return: the content of the generated Docker-compose file
    """
    template_path = f"{__DOCKER_DIR__}docker-compose.yaml"
    if not exists(template_path):
        raise FileNotFoundError(f"Docker Compose template {template_path} not found, check your installtion")
    with open(template_path) as f:
        template = f.read()
    for term, (original, replacement) in __TERMS_TO_BE_REPLACED__.items():
        template = template.replace(original, replacement(locals()[term]))
    return template


def command_to_start_docker_compose(service_name: str, *, in_background: bool = True, force_build: bool = True) -> str:
    """
    Start the Docker-compose service.
    :param service_name: the name of the service to start
    :param in_background: whether to run the service in the background
    :param force_build: whether to force rebuild the service
    :return: the command to run
    """
    cmd = f"docker compose up"
    if in_background:
        cmd += " -d"
    cmd += f" {service_name}"
    if force_build:
        cmd += " --build"
    return cmd
