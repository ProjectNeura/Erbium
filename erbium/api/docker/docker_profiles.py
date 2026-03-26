from os import PathLike, listdir
from typing import Any
from json import dump, load

from erbium.api.docker.docker_compose import create_docker_compose


def docker_profiles_dir(root_dir: str | PathLike[str]) -> str:
    return f"{root_dir}/docker-profiles"


ESCAPE_CHARACTERS: tuple[str, str, str, str] = ("\n", "\r", "\t", " ")


def list_docker_profiles(root_dir: str | PathLike[str]) -> dict[str, dict[str, Any]]:
    """
    :param root_dir: the root directory of the docker-profiles
    :return: service names and corresponding configurations
    """
    dp_dir = docker_profiles_dir(root_dir)
    r = {}
    for compose_config in listdir(dp_dir):
        if not compose_config.endswith(".json"):
            continue
        with open(f"{dp_dir}/{compose_config}") as f:
            r[compose_config[:-5]] = load(f)
    return r


def create_docker_profile(root_dir: str | PathLike[str], service_name: str, password: str, **kwargs) -> None:
    with open(f"{docker_profiles_dir(root_dir)}/{service_name}.yaml", "w") as f:
        f.write(create_docker_compose(service_name, password, **kwargs))
    with open(f"{docker_profiles_dir(root_dir)}/{service_name}.json", "w") as f:
        dump({"service_name": service_name, "password": password, **kwargs}, f)
