# gpu-worker

Worker agent for [GPUBridge](https://github.com/LIU-CS-691/gpu-bridge) — registers with a GPUBridge controller, polls for jobs, and executes them in Docker containers with optional NVIDIA GPU passthrough.

## Install

```bash
pip install gpu-worker
```

## Quick Start

```bash
# Set your invite token (get one from your admin)
export GPU_BRIDGE_INVITE="<invite_token>"

# Register this machine
gpu-worker register --name "My GPU Server"

# Start executing jobs
gpu-worker start --worker-id <WORKER_ID> --gpu
```

## Requirements

- Python 3.11+
- Docker (running)
- NVIDIA Container Toolkit (for GPU jobs)
