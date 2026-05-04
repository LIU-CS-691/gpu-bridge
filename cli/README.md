# gpu-tool

CLI for [GPUBridge](https://github.com/LIU-CS-691/gpu-bridge) — submit and monitor GPU jobs from your terminal.

## Install

```bash
pip install gpu-tool
```

## Quick Start

```bash
# Login with your invite token (get one from your admin)
gpu-tool login <invite_token>

# Check connection
gpu-tool health

# Submit a job
gpu-tool job-create --image my-training-image --cmd "python train.py"

# Watch logs stream in real-time
gpu-tool job-logs --job-id <JOB_ID> --follow
```

## Commands

| Command | Description |
|---|---|
| `login <token>` | Authenticate with an invite token |
| `health` | Check controller connection |
| `workers` | List GPU workers and their status |
| `jobs` | List jobs (filter with `--status`, `--gpu-id`) |
| `job-create` | Submit a new job |
| `job-get` | Get job details |
| `job-logs` | Fetch job logs (`--follow` for streaming) |
