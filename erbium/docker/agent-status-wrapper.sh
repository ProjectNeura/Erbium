#!/usr/bin/env bash

set -u

agent="${ERBIUM_AGENT_NAME:-$(basename "$0")}"
case "$agent" in
  codex|claude) ;;
  *)
    echo "agent-status-wrapper: unsupported agent '$agent'" >&2
    exit 127
    ;;
esac

real_cmd="${ERBIUM_REAL_COMMAND:-/usr/local/bin/$agent}"
poster="${ERBIUM_AGENT_STATUS_POSTER:-/usr/local/bin/agent-status-post.py}"
tail_bytes="${ERBIUM_AGENT_STATUS_TAIL_BYTES:-12000}"
poll_interval="${ERBIUM_AGENT_STATUS_INTERVAL:-1}"
host_name="$(hostname 2>/dev/null || echo node)"
session_id="${ERBIUM_AGENT_SESSION_ID:-$agent-$host_name-$$-$(date +%s)}"

if [ ! -x "$real_cmd" ]; then
  echo "agent-status-wrapper: real command not found at $real_cmd" >&2
  exit 127
fi

if [ "$(readlink -f "$real_cmd")" = "$(readlink -f "$0")" ]; then
  echo "agent-status-wrapper: refusing to call itself for $agent" >&2
  exit 127
fi

task="$agent $*"
output_file="$(mktemp -t "erbium-$agent-output.XXXXXX")"
poster_pid=""

post_status() {
  local state="$1"
  local exit_code="${2:-}"
  local input_file="${3:-/dev/null}"
  local args=(--agent "$agent" --session-id "$session_id" --state "$state" --task "$task")

  if [ -n "$exit_code" ]; then
    args+=(--exit-code "$exit_code")
  fi

  python3 "$poster" "${args[@]}" < "$input_file" >/dev/null 2>&1 || true
}

post_tail() {
  if [ -s "$output_file" ]; then
    tail -c "$tail_bytes" "$output_file" > "$output_file.tail" 2>/dev/null || true
    post_status "$1" "${2:-}" "$output_file.tail"
  else
    post_status "$1" "${2:-}"
  fi
}

cleanup() {
  if [ -n "$poster_pid" ]; then
    kill "$poster_pid" >/dev/null 2>&1 || true
  fi
  rm -f "$output_file" "$output_file.tail"
}

stop_heartbeat() {
  if [ -n "$poster_pid" ]; then
    kill "$poster_pid" >/dev/null 2>&1 || true
    wait "$poster_pid" >/dev/null 2>&1 || true
    poster_pid=""
  fi
}

trap cleanup EXIT
trap 'stop_heartbeat; cleanup; exit 130' INT
trap 'stop_heartbeat; cleanup; exit 143' TERM

run_command_with_capture() {
  if command -v script >/dev/null 2>&1 && script --version >/dev/null 2>&1; then
    local cmdline
    printf -v cmdline "%q " "$real_cmd" "$@"
    script -q -f -e -c "$cmdline" "$output_file"
  else
    "$real_cmd" "$@" 2>&1 | tee -a "$output_file"
    return "${PIPESTATUS[0]}"
  fi
}

post_status started
(
  while true; do
    post_tail running
    sleep "$poll_interval"
  done
) &
poster_pid="$!"

run_command_with_capture "$@"
exit_code="$?"

stop_heartbeat
post_tail finished "$exit_code"
exit "$exit_code"
