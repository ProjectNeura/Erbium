from subprocess import run, CompletedProcess, Popen
from typing import Sequence


def run_command(cmd: str | Sequence[str], *, as_root: bool = False) -> CompletedProcess:
    return run(cmd, shell=True, check=True, creationflags=0x08000000 if as_root else 0)


def run_command_async(cmd: str | Sequence[str], *, as_root: bool = False) -> Popen:
    return Popen(cmd, shell=True, creationflags=0x08000000 if as_root else 0)
