from os import PathLike
from os.path import abspath
from pathlib import Path
from subprocess import run

from huggingface_hub import HfApi, create_bucket, sync_bucket

_INIT_SCRIPT: str = f"{abspath(__file__)[:-13]}init.sh"
_WORKSPACE_PATH: Path = Path("/workspace")
_NODE_ID_PATH: Path = _WORKSPACE_PATH / "node_id"
_HF_TOKEN_PATH: Path = _WORKSPACE_PATH / "hf_token"
_IGNORE_PATTERNS: list[str] = ["hf_token", ".cache/huggingface/**"]


def set_node_id(node_id: str) -> None:
    _WORKSPACE_PATH.mkdir(parents=True, exist_ok=True)
    _NODE_ID_PATH.write_text(node_id.strip())


def get_node_id() -> str:
    return _NODE_ID_PATH.read_text().strip()


def set_hf_token(hf_token: str) -> None:
    _WORKSPACE_PATH.mkdir(parents=True, exist_ok=True)
    _HF_TOKEN_PATH.write_text(hf_token.strip())
    _HF_TOKEN_PATH.chmod(0o600)


def get_hf_token() -> str:
    return _HF_TOKEN_PATH.read_text().strip()


def initialize(node_id: str, hf_token: str) -> None:
    """
    Following @erbium/docker/docker-compose.yaml, initialize the environment.
    """
    run(("bash", _INIT_SCRIPT), check=True)
    set_node_id(node_id)
    set_hf_token(hf_token)


def _get_hf_api() -> HfApi:
    return HfApi(token=get_hf_token())


def _get_bucket_id(hf_bucket: str) -> str:
    if "/" in hf_bucket:
        return hf_bucket
    api = _get_hf_api()
    user = api.whoami()
    return f"{user['name']}/{hf_bucket}"


def _create_bucket(hf_bucket: str) -> str:
    bucket_url = create_bucket(hf_bucket, private=True, exist_ok=True, token=get_hf_token())
    return bucket_url.bucket_id


def _get_bucket_prefix() -> str:
    node_id = get_node_id()
    if not node_id:
        raise ValueError("The stored node_id is empty. Run initialize(node_id, hf_token) first.")
    return node_id


def _get_bucket_uri(bucket_id: str) -> str:
    return f"hf://buckets/{bucket_id}/{_get_bucket_prefix()}"


def _sync_bucket(source: str | Path, destination: str | Path, *, delete: bool = False) -> None:
    sync_bucket(
        str(source),
        str(destination),
        delete=delete,
        exclude=_IGNORE_PATTERNS,
        token=get_hf_token()
    )


def upload_workspace(*, workspace: str | PathLike[str] = "/workspace",
                     hf_bucket: str = "ProjectNeura/ErbiumOnVast") -> None:
    workspace_path = Path(workspace).expanduser().resolve()
    if not workspace_path.is_dir():
        raise FileNotFoundError(f"Workspace directory not found: {workspace_path}")
    bucket_id = _create_bucket(hf_bucket)
    _sync_bucket(workspace_path, _get_bucket_uri(bucket_id), delete=True)


def download_workspace(*, workspace: str | PathLike[str] = "/workspace",
                       hf_bucket: str = "ProjectNeura/ErbiumOnVast") -> None:
    workspace_path = Path(workspace).expanduser().resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)
    bucket_id = _get_bucket_id(hf_bucket)
    _sync_bucket(_get_bucket_uri(bucket_id), workspace_path)
