import os

# Set test environment BEFORE any controller imports
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///./test.db"
os.environ["API_TOKEN"] = "test-token"

from controller.app.db import Base, engine  # noqa: E402
from controller.app.main import create_app  # noqa: E402
import controller.app.models  # noqa: E402, F401
from fastapi.testclient import TestClient  # noqa: E402

# Create tables once at module level
Base.metadata.drop_all(bind=engine)  # Clean slate
Base.metadata.create_all(bind=engine)


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
    headers = {"X-API-Token": "test-token"}

    r = client.post("/workers/register", json={"name": "John's GPU"}, headers=headers)
    assert r.status_code == 200
    worker_id = r.json()["id"]

    r = client.get("/workers", headers=headers)
    assert r.status_code == 200
    workers = r.json()
    assert any(w["id"] == worker_id for w in workers)


def test_create_job_requires_worker():
    client = get_test_client()
    headers = {"X-API-Token": "test-token"}

    r = client.post(
        "/jobs",
        json={"worker_id": "nope", "image": "img", "command": "echo hi"},
        headers=headers,
    )
    assert r.status_code == 404
