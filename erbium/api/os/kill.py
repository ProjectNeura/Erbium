from subprocess import run


def kill_all_sessions(username: str, *, force: bool = False, use_loginctl: bool = False) -> None:
    if use_loginctl:
        result = run(["loginctl", "terminate-user", username], capture_output=True, text=True)
        if result.returncode == 0:
            return
    signal = "-KILL" if force else "-TERM"
    result = run(["pkill", signal, "-u", username], capture_output=True, text=True)
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.strip() or f"pkill failed for user {username}")
