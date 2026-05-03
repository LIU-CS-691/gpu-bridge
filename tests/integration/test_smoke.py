import os
from pathlib import Path

import requests
from dotenv import load_dotenv

env_path = Path.cwd() / ".env"
if env_path.exists():
    load_dotenv(env_path)

SERVER = os.getenv("GPU_BRIDGE_SERVER", "http://localhost:8000")
TOKEN = os.getenv("GPU_BRIDGE_TOKEN", "dev-token")
HEADERS = {"X-API-Token": TOKEN}


def test_health_live():
    r = requests.get(f"{SERVER}/health", timeout=10)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register_worker_live():
    r = requests.post(
        f"{SERVER}/workers/register",
        json={"name": "Integration GPU"},
        headers=HEADERS,
        timeout=10,
    )
    assert r.status_code == 200
    assert "id" in r.json()


def test_full_job_lifecycle():
    """Register worker → create job → claim → stream logs → complete → verify."""
    # Register
    r = requests.post(
        f"{SERVER}/workers/register",
        json={"name": "Lifecycle GPU"},
        headers=HEADERS,
        timeout=10,
    )
    assert r.status_code == 200
    worker_id = r.json()["id"]

    # Heartbeat
    r = requests.post(
        f"{SERVER}/workers/{worker_id}/heartbeat",
        headers=HEADERS,
        timeout=10,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "online"

    # Create job
    r = requests.post(
        f"{SERVER}/jobs",
        json={"worker_id": worker_id, "image": "alpine", "command": "echo lifecycle"},
        headers=HEADERS,
        timeout=10,
    )
    assert r.status_code == 200
    job_id = r.json()["id"]
    assert r.json()["status"] == "PENDING"

    # List jobs filtered
    r = requests.get(
        f"{SERVER}/jobs",
        params={"worker_id": worker_id, "status": "PENDING"},
        headers=HEADERS,
        timeout=10,
    )
    assert r.status_code == 200
    assert any(j["id"] == job_id for j in r.json())

    # Claim
    r = requests.patch(
        f"{SERVER}/jobs/{job_id}/claim",
        headers=HEADERS,
        timeout=10,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "RUNNING"

    # Stream logs
    r = requests.patch(
        f"{SERVER}/jobs/{job_id}/logs",
        json={"data": "lifecycle output\n"},
        headers=HEADERS,
        timeout=10,
    )
    assert r.status_code == 200

    # Read logs with offset
    r = requests.get(
        f"{SERVER}/jobs/{job_id}/logs",
        params={"offset": 0},
        headers=HEADERS,
        timeout=10,
    )
    assert r.status_code == 200
    assert "lifecycle output" in r.json()["logs"]

    # Complete
    r = requests.patch(
        f"{SERVER}/jobs/{job_id}/complete",
        json={"status": "SUCCEEDED"},
        headers=HEADERS,
        timeout=10,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "SUCCEEDED"

    # Verify final state
    r = requests.get(
        f"{SERVER}/jobs/{job_id}",
        headers=HEADERS,
        timeout=10,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "SUCCEEDED"
    assert "lifecycle output" in r.json()["logs"]
