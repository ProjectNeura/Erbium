#!/usr/bin/env bash
set -euo pipefail
export BORG_REPO=/workspace/output/backup
borg create --stats --exclude /workspace/output/backup ::'{hostname}-{now:%Y-%m-%d_%H-%M-%S}' /workspace/output
borg prune --list --keep-daily=7 --keep-weekly=4 --keep-monthly=6