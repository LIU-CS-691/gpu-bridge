import os
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(__file__).resolve().parents[2] / ".env"
if env_path.exists():
    load_dotenv(env_path, override=False)

os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL", "postgresql+psycopg://gpu:gpu@localhost:5433/gpu_bridge_test"
)
os.environ["API_TOKEN"] = "test-token"

from controller.app.db import Base, engine  # noqa: E402
from controller.app.main import create_app  # noqa: E402
import controller.app.models  # noqa: E402, F401
from fastapi.testclient import TestClient  # noqa: E402

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

HEADERS = {"X-API-Token": "test-token"}


def get_test_client():
    app = create_app()
    return TestClient(app)


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


def test_create_job_requires_worker():
    client = get_test_client()
    r = client.post(
        "/jobs",
        json={"worker_id": "nope", "image": "img", "command": "echo hi"},
        headers=HEADERS,
    )
    assert r.status_code == 404


def test_job_claim_and_complete():
    client = get_test_client()

    r = client.post("/workers/register", json={"name": "Test GPU"}, headers=HEADERS)
    worker_id = r.json()["id"]

    r = client.post(
        "/jobs",
        json={"worker_id": worker_id, "image": "alpine", "command": "echo ok"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    job = r.json()
    assert job["status"] == "PENDING"
    job_id = job["id"]

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

    r = client.post("/workers/register", json={"name": "Filter GPU"}, headers=HEADERS)
    worker_id = r.json()["id"]

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

    r = client.post("/workers/register", json={"name": "Trans GPU"}, headers=HEADERS)
    worker_id = r.json()["id"]

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

    r = client.post("/workers/register", json={"name": "Log GPU"}, headers=HEADERS)
    worker_id = r.json()["id"]

    r = client.post(
        "/jobs",
        json={"worker_id": worker_id, "image": "alpine", "command": "echo streaming"},
        headers=HEADERS,
    )
    job_id = r.json()["id"]

    # Can't append logs to PENDING job
    r = client.patch(f"/jobs/{job_id}/logs", json={"data": "chunk1"}, headers=HEADERS)
    assert r.status_code == 409

    # Claim the job
    client.patch(f"/jobs/{job_id}/claim", headers=HEADERS)

    # Append first chunk
    r = client.patch(f"/jobs/{job_id}/logs", json={"data": "line 1\n"}, headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["logs"] == "line 1\n"

    # Append second chunk
    r = client.patch(f"/jobs/{job_id}/logs", json={"data": "line 2\n"}, headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["logs"] == "line 1\nline 2\n"

    # GET logs with offset
    r = client.get(f"/jobs/{job_id}/logs?offset=0", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["logs"] == "line 1\nline 2\n"

    r = client.get(f"/jobs/{job_id}/logs?offset=7", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["logs"] == "line 2\n"

    # Complete — logs should persist
    client.patch(
        f"/jobs/{job_id}/complete", json={"status": "SUCCEEDED"}, headers=HEADERS
    )

    r = client.get(f"/jobs/{job_id}/logs?offset=0", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["logs"] == "line 1\nline 2\n"
    assert r.json()["status"] == "SUCCEEDED"
