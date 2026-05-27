#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_HOME="${ROOT_HOME:-/root}"
WORKSPACE="${WORKSPACE:-/workspace}"
APP_DIR="${APP_DIR:-${WORKSPACE}/app}"
INPUT_DIR="${INPUT_DIR:-${WORKSPACE}/input}"
OUTPUT_DIR="${OUTPUT_DIR:-${WORKSPACE}/output}"
VENV_DIR="${VENV_DIR:-${WORKSPACE}/venv}"
PVENVS_DIR="${PVENVS_DIR:-${WORKSPACE}/pvenvs}"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"
UV_BIN="${UV_BIN:-${ROOT_HOME}/.local/bin/uv}"
ERBIUM_PACKAGE="${ERBIUM_PACKAGE:-git+https://github.com/ProjectNeura/Erbium}"

export NVIDIA_VISIBLE_DEVICES="${NVIDIA_VISIBLE_DEVICES:-all}"
export NVIDIA_DRIVER_CAPABILITIES="${NVIDIA_DRIVER_CAPABILITIES:-compute,utility}"

log() {
  printf '[init] %s\n' "$*"
}

require_root() {
  if [ "$(id -u)" -eq 0 ]; then
    return
  fi
  if command -v sudo >/dev/null 2>&1; then
    exec sudo -E bash "$0" "$@"
  fi
  printf 'init.sh must run as root, or sudo must be available.\n' >&2
  exit 1
}

write_profile_script() {
  cat > /etc/profile.d/venv.sh <<PROFILE
VENV="${VENV_DIR}"
if [ -n "\$PS1" ] && [ -f "\$VENV/bin/activate" ]; then
  . "\$VENV/bin/activate"
fi
export PATH="\$HOME/.local/bin:\$PATH"
PROFILE
  chmod 0644 /etc/profile.d/venv.sh
}

write_motd() {
  cat > /etc/motd <<'MOTD'
Welcome to Erbium!

This is part of Project Neura's Internal Computing Platform. Authorized access only.

To report issues, please join #erbium on Slack.
MOTD
  chmod 0644 /etc/motd
}

write_skill() {
  install -d -m 0755 /opt/erbium-skills/use-erbium
  if [ -f /opt/erbium-skills/use-erbium/SKILL.md ]; then
    return
  fi

  cat > /opt/erbium-skills/use-erbium/SKILL.md <<'SKILL'
---
name: use-erbium
description: Guidelines for running ML research experiments on Erbium, a remote VM accessed via Jupyter. Use when the user mentions Erbium, runs training/eval/inference on this machine, asks where to put source code, model weights, datasets, predictions, or metrics, or needs to know GPU usage limits or the /workspace directory layout (app/input/output/venv).
---

# Use Erbium

Erbium is the remote computer you are currently running on. Users connect to it through a small remoting tool and drive ML research experiments from Jupyter. The conventions below keep multiple projects and users from stepping on each other.

## GPU usage

- Cap each job at 95% of total GPU memory / utilization. Leave at least 5% headroom so other processes and the OS stay responsive.
- Before launching a long run, check current usage with `nvidia-smi`. If existing processes already consume significant GPU, scale your job down or wait.
- For PyTorch, prefer setting an explicit fraction, such as `torch.cuda.set_per_process_memory_fraction(0.95)`, or batch-size limits over relying on dynamic allocation.

## Filesystem layout

All project data lives under `/workspace`. There are four persistent folders, and everything in them survives restarts:

```text
/workspace/app/<project_name>/      # source code / working tree for the project
/workspace/input/<project_name>/    # pretrained weights, datasets
/workspace/output/<project_name>/   # metrics, predictions, trained weights
/workspace/venv/                    # shared Python virtualenv
```

Rules:

- Use one folder per research project, mirrored under `app/`, `input/`, and `output/`.
- Keep source code in `/workspace/app/<project>/`.
- Keep datasets and pretrained weights in `/workspace/input/<project>/`.
- Keep checkpoints, metrics, predictions, plots, and logs in `/workspace/output/<project>/`.
- Install shared Python dependencies into `/workspace/venv/`.
- Do not write experiment artifacts to `$HOME`.

## Quick checks before a long run

- `nvidia-smi` to confirm GPU headroom.
- `df -h /workspace` to confirm free space.
- Confirm output paths are under `/workspace/output/<project>/`.
SKILL
}

install_packages() {
  log "Installing apt packages"
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ca-certificates \
    curl \
    unzip \
    zip \
    wget \
    git \
    gnupg \
    python3.12 \
    python3.12-venv \
    tmux \
    vim \
    nodejs \
    npm \
    bubblewrap
}

install_node_tools() {
  log "Installing global node CLIs"
  npm i -g @openai/codex @anthropic-ai/claude-code
}

configure_workspace() {
  log "Configuring root workspace"

  install -d -o root -g root \
    "${APP_DIR}" \
    "${INPUT_DIR}" \
    "${OUTPUT_DIR}" \
    "${VENV_DIR}" \
    "${PVENVS_DIR}"

  chown -R root:root "${APP_DIR}" "${INPUT_DIR}" "${OUTPUT_DIR}" "${VENV_DIR}" "${PVENVS_DIR}"
}

configure_skills() {
  log "Configuring Codex and Claude skills"
  write_skill
  install -d -o root -g root \
    "${ROOT_HOME}/.claude/skills/use-erbium" \
    "${ROOT_HOME}/.codex/skills/use-erbium"
  ln -sfn /opt/erbium-skills/use-erbium/SKILL.md "${ROOT_HOME}/.claude/skills/use-erbium/SKILL.md"
  ln -sfn /opt/erbium-skills/use-erbium/SKILL.md "${ROOT_HOME}/.codex/skills/use-erbium/SKILL.md"
}

install_uv_and_python_env() {
  log "Installing uv for root"
  curl -LsSf https://astral.sh/uv/install.sh | HOME="${ROOT_HOME}" sh

  if [ ! -x "${VENV_DIR}/bin/python" ]; then
    log "Creating Python virtualenv at ${VENV_DIR}"
    HOME="${ROOT_HOME}" "${UV_BIN}" venv --python "${PYTHON_BIN}" "${VENV_DIR}"
  fi

  if ! "${VENV_DIR}/bin/python" -c "import erbium, huggingface_hub, torch, torchvision" >/dev/null 2>&1; then
    log "Installing Python packages"
    HOME="${ROOT_HOME}" "${UV_BIN}" pip install --python "${VENV_DIR}/bin/python" torch torchvision huggingface-hub "${ERBIUM_PACKAGE}"
  fi
}

configure_process_limits() {
  ulimit -l unlimited >/dev/null 2>&1 || true
  ulimit -s 65536 >/dev/null 2>&1 || true
}

main() {
  require_root "$@"
  install_packages
  install_node_tools
  configure_workspace
  write_profile_script
  write_motd
  configure_skills
  install_uv_and_python_env
  configure_process_limits

  log "Environment setup complete"
}

main "$@"
