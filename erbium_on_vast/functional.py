from os import PathLike
from os.path import abspath
from pathlib import Path
from subprocess import run
from huggingface_hub import HfApi, snapshot_download

_INIT_SCRIPT: str = f"{abspath(__file__)[:-13]}init.sh"
_WORKSPACE_REPO_TYPE: str = "dataset"
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
    try:
        from huggingface_hub import HfApi
    except ImportError as exc:
        raise RuntimeError("Install huggingface-hub to upload or download a workspace.") from exc
    return HfApi(token=get_hf_token())


def _get_repo_id(api: HfApi, hf_repo: str) -> str:
    if "/" in hf_repo:
        return hf_repo
    user = api.whoami()
    return f"{user['name']}/{hf_repo}"


def _get_revision() -> str:
    node_id = get_node_id()
    if not node_id:
        raise ValueError("The stored node_id is empty. Run initialize(node_id, hf_token) first.")
    return node_id


def upload_workspace(*, workspace: str | PathLike[str] = "/workspace", hf_repo: str = "ErbiumOnVast") -> None:
    workspace_path = Path(workspace).expanduser().resolve()
    if not workspace_path.is_dir():
        raise FileNotFoundError(f"Workspace directory not found: {workspace_path}")
    token = get_hf_token()
    revision = _get_revision()
    api = _get_hf_api()
    repo_id = _get_repo_id(api, hf_repo)
    api.create_repo(repo_id=repo_id, repo_type=_WORKSPACE_REPO_TYPE, private=True, exist_ok=True)
    api.create_branch(repo_id=repo_id, branch=revision, repo_type=_WORKSPACE_REPO_TYPE, exist_ok=True)
    api.upload_folder(
        repo_id=repo_id,
        folder_path=workspace_path,
        repo_type=_WORKSPACE_REPO_TYPE,
        revision=revision,
        token=token,
        ignore_patterns=_IGNORE_PATTERNS,
        delete_patterns="*",
        commit_message=f"Upload workspace from {revision}"
    )


def download_workspace(*, workspace: str | PathLike[str] = "/workspace", hf_repo: str = "ErbiumOnVast") -> None:
    token = get_hf_token()
    revision = _get_revision()
    api = _get_hf_api()
    repo_id = _get_repo_id(api, hf_repo)
    workspace_path = Path(workspace).expanduser().resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=repo_id,
        repo_type=_WORKSPACE_REPO_TYPE,
        revision=revision,
        local_dir=workspace_path,
        token=token
    )
