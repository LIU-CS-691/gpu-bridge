import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///./test.db"
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

    # Double claim should fail
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

    # Complete again should fail
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

    # Heartbeat for non-existent worker
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

    # Can't complete a PENDING job (must claim first)
    r = client.patch(
        f"/jobs/{job_id}/complete",
        json={"status": "SUCCEEDED"},
        headers=HEADERS,
    )
    assert r.status_code == 409
