---
name: use-erbium
description: Guidelines for running ML research experiments on Erbium, a remote VM accessed via Jupyter. Use when the user mentions Erbium, runs training/eval/inference on this machine, asks where to put source code, model weights, datasets, predictions, or metrics, or needs to know GPU usage limits or the /workspace directory layout (app/input/output/venv).
---

# Use Erbium

Erbium is the remote computer you are currently running on. Users connect to it through a small remoting tool and drive ML research experiments from Jupyter. The conventions below keep multiple projects and users from stepping on each other.

## GPU usage

- Cap each job at **95% of total GPU memory / utilization**. Leave at least 5% headroom so other processes (and the OS) stay responsive.
- Before launching a long run, check current usage with `nvidia-smi`. If existing processes already consume significant GPU, scale your job down or wait.
- For PyTorch, prefer setting an explicit fraction (e.g. `torch.cuda.set_per_process_memory_fraction(0.95)`) or batch-size limits over relying on dynamic allocation.

## Filesystem layout

All project data lives under `/workspace`. There are four persistent folders — everything in them survives container restarts:

```
/workspace/app/<project_name>/      # source code / working tree for the project
/workspace/input/<project_name>/    # read-only-ish: pretrained weights, datasets
/workspace/output/<project_name>/   # writable: metrics, predictions, trained weights
/workspace/venv/                    # shared Python virtualenv (pip-installed deps)
```

Rules:

- **One folder per research project**, named after the project, mirrored under `app/`, `input/`, and `output/`. Use the same `<project_name>` on all three sides.
- **`/workspace/app/<project>/`** holds the project's *code*: cloned repo, scripts, notebooks, configs. This is where you `cd` to run things. Keep code here, not in `input/` or `output/`.
- **`/workspace/input/<project>/`** holds things that come *into* the experiment: pretrained model weights, tokenizers, raw or preprocessed datasets. Treat as a stable cache — don't overwrite unless you mean to.
- **`/workspace/output/<project>/`** holds things the experiment *produces*: training checkpoints, eval metrics (json/csv), inference predictions, plots, logs. Anything reproducible from code + inputs belongs here.
- **`/workspace/venv/`** is a single Python venv shared across all projects. Install deps here with `pip install ...`; do not create per-project venvs unless dependency conflicts force it.
- Do not write experiment artifacts to `app/<project>/` or to `$HOME`. Keep code separate from data.

## When starting a new project

1. Pick a short, lowercase `<project_name>` (e.g. `llmoe_baseline_avg_pooling`).
2. Create `/workspace/app/<project_name>/`, `/workspace/input/<project_name>/`, and `/workspace/output/<project_name>/` before the first run.
3. If you're unsure which `<project_name>` to use, ask the user rather than guessing — name collisions are annoying to fix later.

## Quick checks before a long run

- `nvidia-smi` — confirm you have GPU headroom and no orphan processes.
- `df -h /workspace` — confirm there's space for checkpoints/outputs.
- Output path is under `/workspace/output/<project>/`, not the code dir or `/tmp`.
