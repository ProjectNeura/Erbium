#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
import json
import os
import sys
from urllib.parse import quote
from urllib.error import URLError
from urllib.request import Request, urlopen


def main() -> int:
    parser = ArgumentParser(description="Post Erbium agent status updates.")
    parser.add_argument("--agent", choices=("codex", "claude"), required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--state", choices=("started", "running", "finished", "failed", "idle"), required=True)
    parser.add_argument("--task", default="")
    parser.add_argument("--exit-code", type=int)
    parser.add_argument("--url")
    parser.add_argument("--timeout", type=float, default=1.5)
    args = parser.parse_args()

    output_chunk = sys.stdin.read()
    base_url = os.environ.get("ERBIUM_AGENT_STATUS_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    url = args.url or os.environ.get("ERBIUM_AGENT_STATUS_URL")
    if not url:
        session_id = quote(args.session_id, safe="")
        url = f"{base_url}/agent_status/{args.agent}/{session_id}"
    payload = {
        "state": args.state,
        "session_id": args.session_id,
        "task": args.task,
        "output_chunk": output_chunk,
        "exit_code": args.exit_code,
    }
    data = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=args.timeout) as response:
            response.read()
    except (OSError, URLError):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
