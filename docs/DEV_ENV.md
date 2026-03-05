# Development Environment & Procedures (Milestone)

This doc explains how to provision the same environment across multiple computers and run the standard dev workflows.

## Version control
- Host the repo on GitHub/GitLab.
- Use `main` as protected branch.
- Work on feature branches:
  - `git checkout -b feature/<short-name>`
- Open a PR and require at least 1 review.

## Prerequisites
- Git
- Docker + Compose (`docker compose version`)
- Python 3.11+ (or use the Dev Container)

## Option A (recommended): VS Code Dev Container
1. Install Docker + VS Code.
2. Install the VS Code **Dev Containers** extension.
3. `git clone <repo>`
4. Open the folder in VS Code → “Reopen in Container”.
5. The container runs `postCreateCommand` to install dependencies.

## Option B: Local Python venv
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements-dev.txt -r controller/requirements.txt
pip install -e ./cli -e ./worker
```

## Build / Run (Controller + DB)
Start Postgres + Controller:
```bash
make up
```

Verify:
```bash
curl -s http://localhost:8000/health
```

Stop:
```bash
make down
```

## Database (relevant)
- Postgres runs via Docker Compose (service `db`).
- For this milestone, the controller auto-creates tables on startup using SQLAlchemy `create_all`.
- Connection string is injected via `DATABASE_URL`.

## Unit tests
Unit tests use in-memory SQLite (no Docker required):
```bash
make test
```

## Integration tests
Integration tests call the running controller at `http://localhost:8000`:
```bash
make up
make itest
```

You can override the server/token:
```bash
GPU_BRIDGE_SERVER=http://localhost:8000 GPU_BRIDGE_TOKEN=dev-token make itest
```

## Mocks / external services
At this milestone:
- No real external services (Tailscale, Docker GPU runtime, registries) are required.
- Tests do not call Docker or GPUs.
- For later milestones, Docker/GPU execution will be wrapped behind an interface so it can be mocked in tests.

## Deploy (relevant)
For this milestone, “deploy” means running via Docker Compose on any machine:
```bash
docker compose up -d --build
```
