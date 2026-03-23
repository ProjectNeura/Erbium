from subprocess import run, CompletedProcess


def run_command(cmd: str, *, as_admin: bool = False) -> CompletedProcess:
    return run(cmd, shell=True, check=True, creationflags=0x08000000 if as_admin else 0)
