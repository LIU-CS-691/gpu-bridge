# GPUBridge Sprint Plan

## Sprint 1 — Foundation (Completed)

**Goal:** Reproducible dev environment + minimal working system with controller, CLI, and worker registration.

### Delivered

#### Controller API
- [x] FastAPI app with health, worker registration, list workers, create/get job endpoints
- [x] SQLAlchemy models (Worker, Job) with Postgres support
- [x] Pydantic request/response schemas
- [x] Token-based auth middleware (`X-API-Token`)
- [x] Dockerfile for containerized deployment

#### CLI (`gpu-tool`)
- [x] Commands: health, workers, job-create, job-get, login (stub)

#### Worker (`gpu-worker`)
- [x] Register command — register a machine as a worker

#### Infrastructure & CI
- [x] Docker Compose (Postgres + Controller)
- [x] Makefile (up, down, setup, test, itest, lint, fmt)
- [x] VS Code Dev Container
- [x] GitHub Actions CI (lint, unit tests, integration tests)
- [x] Unit tests (3) + Integration tests (2)

#### Bug Fixes
- [x] Fix CLI auth header — sends `Authorization: Bearer` but controller expects `X-API-Token`
- [x] Fix CLI login — persist credentials instead of just comparing tokens
- [x] Add `python-dotenv` to cli and worker `pyproject.toml` dependencies

#### Controller Enhancements
- [x] Job claim endpoint (`PATCH /jobs/{job_id}/claim`) — PENDING → RUNNING, prevent double-assignment
- [x] Job completion endpoint (`PATCH /jobs/{job_id}/complete`) — RUNNING → SUCCEEDED/FAILED with logs
- [x] Job status state machine enforcement
- [x] Job logs storage
- [x] List jobs endpoint (`GET /jobs`) with filtering by worker_id and status
- [x] Worker heartbeat tracking — mark stale workers offline

#### CLI Enhancements
- [x] `gpu-tool jobs` — list jobs with filters
- [x] `gpu-tool job-logs` — fetch job output
- [x] `gpu-tool workers` — show online/offline status, GPU info

#### Testing
- [x] Unit tests for job state transitions and heartbeat logic

---

## Sprint 2 — Full Job Execution & Networking (Target)

**Goal:** End-to-end system where workers poll for jobs, execute them as Docker containers on GPU machines, report results, and communicate over Tailscale.

### Worker Job Execution
- [ ] Worker poll loop — `gpu-worker start` continuously polls for PENDING jobs
- [ ] Docker container execution via Docker SDK — pull image, run command, capture output
- [ ] GPU passthrough using NVIDIA Container Toolkit
- [ ] Timeout handling — configurable per-job, kill container if exceeded
- [ ] Log capture — stdout/stderr stored with job result
- [ ] GPU capability reporting — detect GPU type, VRAM, availability via `pynvml`/`nvidia-smi`
- [ ] Worker heartbeat — periodic ping to controller

### Controller Enhancements
- [ ] Job scheduling — match job requirements to worker GPU capabilities
- [ ] Job queuing and priority
- [ ] Proper auth (JWT / OAuth / scoped API keys)
- [ ] Alembic DB migrations

### Networking
- [ ] Tailscale integration — controller and workers communicate over Tailscale IPs
- [ ] Worker resource monitoring (GPU utilization, VRAM, temperature)

### Testing
- [ ] Integration test for full job lifecycle (submit → execute → complete)
- [ ] Worker tests with mocked Docker SDK

### Prerequisites

| Dependency | Purpose |
|---|---|
| `docker` Python SDK | Workers run containers |
| Docker daemon on worker machines | Container runtime |
| NVIDIA Container Toolkit (`nvidia-docker2`) | GPU passthrough to containers |
| `pynvml` | GPU detection and monitoring |
| Tailscale account + auth keys | Multi-machine networking |
| Alembic | Schema migrations |
