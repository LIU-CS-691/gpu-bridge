import base64
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parents[2] / ".env"
if env_path.exists():
    load_dotenv(env_path, override=False)

os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL", "postgresql+psycopg://gpu:gpu@localhost:5433/gpu_bridge_test"
)
os.environ["BOOTSTRAP_TOKEN"] = "test-token"
os.environ["SERVER_URL"] = "http://localhost:8000"

from controller.app.db import Base, engine  # noqa: E402
from controller.app.main import create_app  # noqa: E402
import controller.app.models  # noqa: E402, F401
from fastapi.testclient import TestClient  # noqa: E402

ADMIN_HEADERS = {"X-API-Token": "test-token"}
HEADERS = ADMIN_HEADERS


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def get_test_client():
    app = create_app()
    return TestClient(app)


def _register_online_worker(client, name="Test GPU"):
    """Register a worker and send heartbeat so it's online."""
    r = client.post("/workers/register", json={"name": name}, headers=HEADERS)
    worker_id = r.json()["id"]
    client.post(f"/workers/{worker_id}/heartbeat", headers=HEADERS)
    return worker_id


def test_health_ok():
    client = get_test_client()
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register_and_list_workers():
    client = get_test_client()
    r = client.post("/workers/register", json={"name": "John's GPU"}, headers=HEADERS)
    assert r.status_code == 200
    worker = r.json()
    assert "id" in worker
    assert worker["status"] == "unknown"

    r = client.get("/workers", headers=HEADERS)
    assert r.status_code == 200
    assert any(w["id"] == worker["id"] for w in r.json())


def test_create_job_requires_valid_worker():
    client = get_test_client()
    r = client.post(
        "/jobs",
        json={"worker_id": "nope", "image": "img", "command": "echo hi"},
        headers=HEADERS,
    )
    assert r.status_code == 404


def test_job_with_explicit_worker():
    client = get_test_client()
    worker_id = _register_online_worker(client)

    r = client.post(
        "/jobs",
        json={"worker_id": worker_id, "image": "alpine", "command": "echo ok"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    job = r.json()
    assert job["status"] == "PENDING"
    assert job["worker_id"] == worker_id


def test_job_claim_and_complete():
    client = get_test_client()
    worker_id = _register_online_worker(client)

    r = client.post(
        "/jobs",
        json={"worker_id": worker_id, "image": "alpine", "command": "echo ok"},
        headers=HEADERS,
    )
    job_id = r.json()["id"]

    r = client.patch(f"/jobs/{job_id}/claim", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["status"] == "RUNNING"

    r = client.patch(f"/jobs/{job_id}/claim", headers=HEADERS)
    assert r.status_code == 409

    r = client.patch(
        f"/jobs/{job_id}/complete",
        json={"status": "SUCCEEDED", "logs": "hello world"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "SUCCEEDED"
    assert r.json()["logs"] == "hello world"

    r = client.patch(
        f"/jobs/{job_id}/complete",
        json={"status": "FAILED"},
        headers=HEADERS,
    )
    assert r.status_code == 409


def test_list_jobs_with_filters():
    client = get_test_client()
    worker_id = _register_online_worker(client, "Filter GPU")

    client.post(
        "/jobs",
        json={"worker_id": worker_id, "image": "img1", "command": "cmd1"},
        headers=HEADERS,
    )
    client.post(
        "/jobs",
        json={"worker_id": worker_id, "image": "img2", "command": "cmd2"},
        headers=HEADERS,
    )

    r = client.get("/jobs", headers=HEADERS)
    assert r.status_code == 200
    assert len(r.json()) >= 2

    r = client.get(f"/jobs?worker_id={worker_id}", headers=HEADERS)
    assert r.status_code == 200
    assert all(j["worker_id"] == worker_id for j in r.json())

    r = client.get("/jobs?status=PENDING", headers=HEADERS)
    assert r.status_code == 200
    assert all(j["status"] == "PENDING" for j in r.json())


def test_worker_heartbeat():
    client = get_test_client()

    r = client.post("/workers/register", json={"name": "HB GPU"}, headers=HEADERS)
    worker_id = r.json()["id"]
    assert r.json()["status"] == "unknown"

    r = client.post(f"/workers/{worker_id}/heartbeat", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["status"] == "online"
    assert r.json()["last_heartbeat"] is not None

    r = client.post("/workers/nonexistent/heartbeat", headers=HEADERS)
    assert r.status_code == 404


def test_invalid_status_transition():
    client = get_test_client()
    worker_id = _register_online_worker(client, "Trans GPU")

    r = client.post(
        "/jobs",
        json={"worker_id": worker_id, "image": "img", "command": "cmd"},
        headers=HEADERS,
    )
    job_id = r.json()["id"]

    r = client.patch(
        f"/jobs/{job_id}/complete",
        json={"status": "SUCCEEDED"},
        headers=HEADERS,
    )
    assert r.status_code == 409


def test_streaming_logs():
    client = get_test_client()
    worker_id = _register_online_worker(client, "Log GPU")

    r = client.post(
        "/jobs",
        json={"worker_id": worker_id, "image": "alpine", "command": "echo streaming"},
        headers=HEADERS,
    )
    job_id = r.json()["id"]

    r = client.patch(f"/jobs/{job_id}/logs", json={"data": "chunk1"}, headers=HEADERS)
    assert r.status_code == 409

    client.patch(f"/jobs/{job_id}/claim", headers=HEADERS)

    r = client.patch(f"/jobs/{job_id}/logs", json={"data": "line 1\n"}, headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["logs"] == "line 1\n"

    r = client.patch(f"/jobs/{job_id}/logs", json={"data": "line 2\n"}, headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["logs"] == "line 1\nline 2\n"

    r = client.get(f"/jobs/{job_id}/logs?offset=0", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["logs"] == "line 1\nline 2\n"

    r = client.get(f"/jobs/{job_id}/logs?offset=7", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["logs"] == "line 2\n"

    client.patch(
        f"/jobs/{job_id}/complete", json={"status": "SUCCEEDED"}, headers=HEADERS
    )

    r = client.get(f"/jobs/{job_id}/logs?offset=0", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["logs"] == "line 1\nline 2\n"
    assert r.json()["status"] == "SUCCEEDED"


def test_auto_assign_job():
    """Job without worker_id gets auto-assigned to an online worker."""
    client = get_test_client()
    worker_id = _register_online_worker(client, "Auto GPU")

    r = client.post(
        "/jobs",
        json={"image": "alpine", "command": "echo auto"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    job = r.json()
    assert job["worker_id"] == worker_id
    assert job["status"] == "PENDING"


def test_queued_job_no_workers():
    """Job without worker_id stays QUEUED when no online workers."""
    client = get_test_client()

    r = client.post(
        "/jobs",
        json={"image": "alpine", "command": "echo queued"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    job = r.json()
    assert job["status"] == "QUEUED"
    assert job["worker_id"] is None


def test_queued_job_assigned_on_heartbeat():
    """QUEUED jobs get assigned when a worker sends heartbeat."""
    client = get_test_client()

    r = client.post(
        "/jobs",
        json={"image": "alpine", "command": "echo waiting"},
        headers=HEADERS,
    )
    job_id = r.json()["id"]
    assert r.json()["status"] == "QUEUED"

    r = client.post("/workers/register", json={"name": "Late GPU"}, headers=HEADERS)
    worker_id = r.json()["id"]

    client.post(f"/workers/{worker_id}/heartbeat", headers=HEADERS)

    r = client.get(f"/jobs/{job_id}", headers=HEADERS)
    assert r.json()["status"] == "PENDING"
    assert r.json()["worker_id"] == worker_id


def test_priority_ordering():
    """Higher priority jobs get assigned first."""
    client = get_test_client()
    worker_id = _register_online_worker(client, "Priority GPU")

    client.post(
        "/jobs",
        json={"image": "alpine", "command": "echo low", "priority": 1},
        headers=HEADERS,
    )
    client.post(
        "/jobs",
        json={"image": "alpine", "command": "echo high", "priority": 5},
        headers=HEADERS,
    )

    r = client.get(f"/jobs?worker_id={worker_id}&status=PENDING", headers=HEADERS)
    jobs = r.json()
    assert len(jobs) >= 2
    assert jobs[0]["priority"] >= jobs[1]["priority"]


# --- Auth & API Key tests ---


def test_no_token_returns_401():
    client = get_test_client()
    r = client.get("/workers")
    assert r.status_code == 401


def test_invalid_token_returns_401():
    client = get_test_client()
    r = client.get("/workers", headers={"X-API-Token": "bogus"})
    assert r.status_code == 401


def test_create_and_use_api_key():
    client = get_test_client()

    r = client.post(
        "/api-keys",
        json={"name": "test-user-key", "role": "user"},
        headers=ADMIN_HEADERS,
    )
    assert r.status_code == 200
    key = r.json()["key"]
    assert key.startswith("gpub_")

    user_headers = {"X-API-Token": key}
    r = client.get("/workers", headers=user_headers)
    assert r.status_code == 200


def test_user_key_cannot_manage_keys():
    client = get_test_client()

    r = client.post(
        "/api-keys",
        json={"name": "user-key", "role": "user"},
        headers=ADMIN_HEADERS,
    )
    user_key = r.json()["key"]

    r = client.get("/api-keys", headers={"X-API-Token": user_key})
    assert r.status_code == 403


def test_worker_key_cannot_create_jobs():
    client = get_test_client()

    r = client.post(
        "/api-keys",
        json={"name": "worker-key", "role": "worker"},
        headers=ADMIN_HEADERS,
    )
    worker_key = r.json()["key"]

    r = client.post(
        "/jobs",
        json={"image": "alpine", "command": "echo hi"},
        headers={"X-API-Token": worker_key},
    )
    assert r.status_code == 403


def test_revoke_api_key():
    client = get_test_client()

    r = client.post(
        "/api-keys",
        json={"name": "revoke-me", "role": "user"},
        headers=ADMIN_HEADERS,
    )
    key_id = r.json()["id"]
    key = r.json()["key"]

    r = client.delete(f"/api-keys/{key_id}", headers=ADMIN_HEADERS)
    assert r.status_code == 200
    assert r.json()["is_active"] is False

    r = client.get("/workers", headers={"X-API-Token": key})
    assert r.status_code == 401


def test_list_api_keys():
    client = get_test_client()

    client.post(
        "/api-keys",
        json={"name": "key-a", "role": "user"},
        headers=ADMIN_HEADERS,
    )
    client.post(
        "/api-keys",
        json={"name": "key-b", "role": "worker"},
        headers=ADMIN_HEADERS,
    )

    r = client.get("/api-keys", headers=ADMIN_HEADERS)
    assert r.status_code == 200
    keys = r.json()
    assert len(keys) >= 2
    assert not any("key" in k for k in keys[0])


def test_invite_token():
    client = get_test_client()

    r = client.post(
        "/api-keys",
        json={"name": "invite-test", "role": "user"},
        headers=ADMIN_HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert "invite_token" in data

    decoded = base64.urlsafe_b64decode(data["invite_token"]).decode()
    server, key = decoded.split("|", 1)
    assert server == "http://localhost:8000"
    assert key == data["key"]

    user_headers = {"X-API-Token": key}
    r = client.get("/workers", headers=user_headers)
    assert r.status_code == 200
