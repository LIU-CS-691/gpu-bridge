import os
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load .env from project root if present
env_path = Path.cwd() / ".env"
if env_path.exists():
    load_dotenv(env_path)

SERVER = os.getenv("GPU_BRIDGE_SERVER", "http://localhost:8000")
TOKEN = os.getenv("GPU_BRIDGE_TOKEN", "dev-token")


def test_health_live():
    r = requests.get(f"{SERVER}/health", timeout=10)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register_worker_live():
    r = requests.post(
        f"{SERVER}/workers/register",
        json={"name": "Integration GPU"},
        headers={"X-API-Token": TOKEN},
        timeout=10,
    )
    assert r.status_code == 200
    assert "id" in r.json()
