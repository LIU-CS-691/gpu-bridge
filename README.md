# GPUBridge

This repo is the **intermediate milestone**: a reproducible dev environment + a minimal system.
It includes:
- **Controller API** (FastAPI) + **Postgres** (Docker Compose)
- **CLI** (`gpu-tool`) to call the API
- **Worker CLI** (`gpu-worker`) that registers a worker
- **Unit tests** (pytest, in-memory DB) and **Integration tests** (hit a running controller)

> Networking (Tailscale) will come later, but not required for this milestone.
> Later, we will run the controller and worker over Tailscale IPs.

## Quickstart

### 1) Prereqs
- Git
- Docker + Docker Compose (`docker compose version`)
- Python 3.11+ (optional if you use Dev Container)

### 2) Start services
```bash
make up
```

### 3) Run a quick smoke test
```bash
curl -s http://localhost:8000/health | jq .
```

### 4) Use the CLI
```bash
# in a venv or dev container
make setup

gpu-tool health
gpu-worker # To register as gpu-worker
gpu-tool workers
```

### 5) Run tests
```bash
make test
make itest
```

## Repo layout
- `controller/` FastAPI app (containerized)
- `cli/` Typer-based CLI (installs `gpu-tool`)
- `worker/` Typer-based worker CLI (installs `gpu-worker`)
- `tests/` unit + integration tests
