import base64
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.orm import Session

from . import crud, schemas
from .auth import require_role
from .config import settings
from .db import get_db

HEARTBEAT_STALE_SECONDS = 60


def _run_migrations():
    alembic_cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    alembic_cfg.set_main_option(
        "script_location", str(Path(__file__).resolve().parents[1] / "alembic")
    )
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _run_migrations()
    yield


def _worker_status(w) -> str:
    if not w.last_heartbeat:
        return "unknown"
    age = datetime.now(timezone.utc) - w.last_heartbeat.replace(tzinfo=timezone.utc)
    return "online" if age < timedelta(seconds=HEARTBEAT_STALE_SECONDS) else "offline"


def _worker_out(w) -> schemas.WorkerOut:
    return schemas.WorkerOut(
        id=w.id,
        name=w.name,
        last_heartbeat=w.last_heartbeat.isoformat() if w.last_heartbeat else None,
        status=_worker_status(w),
        gpu_info=w.gpu_info,
    )


def _job_out(j) -> schemas.JobOut:
    return schemas.JobOut(
        id=j.id,
        worker_id=j.worker_id,
        image=j.image,
        command=j.command,
        status=j.status,
        priority=j.priority,
        logs=j.logs,
    )


def create_app() -> FastAPI:
    app = FastAPI(title="GPUBridge Controller", lifespan=lifespan)

    # --- Health ---

    @app.get("/health", response_model=schemas.HealthResponse)
    def health():
        return schemas.HealthResponse(status="ok")

    # --- API Keys (admin only) ---

    @app.post(
        "/api-keys",
        dependencies=[Depends(require_role("admin"))],
        response_model=schemas.ApiKeyOut,
    )
    def create_api_key(payload: schemas.ApiKeyCreate, db: Session = Depends(get_db)):
        k = crud.create_api_key(db, payload.name, payload.role)
        invite_token = base64.urlsafe_b64encode(
            f"{settings.server_url}|{k.key}".encode()
        ).decode()
        return schemas.ApiKeyOut(
            id=k.id,
            key=k.key,
            name=k.name,
            role=k.role,
            is_active=k.is_active,
            invite_token=invite_token,
        )

    @app.get(
        "/api-keys",
        dependencies=[Depends(require_role("admin"))],
        response_model=list[schemas.ApiKeyListOut],
    )
    def list_api_keys(db: Session = Depends(get_db)):
        return [
            schemas.ApiKeyListOut(
                id=k.id, name=k.name, role=k.role, is_active=k.is_active
            )
            for k in crud.list_api_keys(db)
        ]

    @app.delete(
        "/api-keys/{key_id}",
        dependencies=[Depends(require_role("admin"))],
        response_model=schemas.ApiKeyListOut,
    )
    def revoke_api_key(key_id: str, db: Session = Depends(get_db)):
        k = crud.revoke_api_key(db, key_id)
        if not k:
            raise HTTPException(status_code=404, detail="API key not found")
        return schemas.ApiKeyListOut(
            id=k.id, name=k.name, role=k.role, is_active=k.is_active
        )

    # --- Workers (admin, user, worker) ---

    @app.post(
        "/workers/register",
        dependencies=[Depends(require_role("admin", "worker"))],
        response_model=schemas.WorkerOut,
    )
    def register_worker(payload: schemas.WorkerCreate, db: Session = Depends(get_db)):
        gpu_data = (
            [g.model_dump() for g in payload.gpu_info] if payload.gpu_info else None
        )
        w = crud.create_worker(db, payload.name, gpu_info=gpu_data)
        return _worker_out(w)

    @app.get(
        "/workers",
        dependencies=[Depends(require_role("admin", "user", "worker"))],
        response_model=list[schemas.WorkerOut],
    )
    def workers(db: Session = Depends(get_db)):
        return [_worker_out(w) for w in crud.list_workers(db)]

    @app.post(
        "/workers/{worker_id}/heartbeat",
        dependencies=[Depends(require_role("admin", "worker"))],
        response_model=schemas.WorkerOut,
    )
    def worker_heartbeat(
        worker_id: str,
        payload: schemas.WorkerHeartbeat | None = None,
        db: Session = Depends(get_db),
    ):
        gpu_data = None
        if payload and payload.gpu_info:
            gpu_data = [g.model_dump() for g in payload.gpu_info]
        w = crud.heartbeat(db, worker_id, gpu_info=gpu_data)
        if not w:
            raise HTTPException(status_code=404, detail="Worker not found")
        crud.assign_queued_jobs(db)
        return _worker_out(w)

    # --- Jobs ---

    @app.post(
        "/jobs",
        dependencies=[Depends(require_role("admin", "user"))],
        response_model=schemas.JobOut,
    )
    def create_job(payload: schemas.JobCreate, db: Session = Depends(get_db)):
        if payload.worker_id and not crud.get_worker(db, payload.worker_id):
            raise HTTPException(status_code=404, detail="Worker not found")
        j = crud.create_job(
            db,
            image=payload.image,
            command=payload.command,
            priority=payload.priority,
            worker_id=payload.worker_id,
        )
        if j.status == "QUEUED":
            assigned = crud.assign_queued_jobs(db)
            for a in assigned:
                if a.id == j.id:
                    j = a
                    break
        return _job_out(j)

    @app.get(
        "/jobs",
        dependencies=[Depends(require_role("admin", "user", "worker"))],
        response_model=list[schemas.JobOut],
    )
    def list_jobs(
        worker_id: str | None = Query(None),
        status: str | None = Query(None),
        db: Session = Depends(get_db),
    ):
        return [
            _job_out(j) for j in crud.list_jobs(db, worker_id=worker_id, status=status)
        ]

    @app.get(
        "/jobs/{job_id}",
        dependencies=[Depends(require_role("admin", "user", "worker"))],
        response_model=schemas.JobOut,
    )
    def get_job(job_id: str, db: Session = Depends(get_db)):
        j = crud.get_job(db, job_id)
        if not j:
            raise HTTPException(status_code=404, detail="Job not found")
        return _job_out(j)

    @app.patch(
        "/jobs/{job_id}/claim",
        dependencies=[Depends(require_role("admin", "worker"))],
        response_model=schemas.JobOut,
    )
    def claim_job(job_id: str, db: Session = Depends(get_db)):
        j = crud.claim_job(db, job_id)
        if not j:
            raise HTTPException(
                status_code=409, detail="Job not found or not in PENDING state"
            )
        return _job_out(j)

    @app.patch(
        "/jobs/{job_id}/complete",
        dependencies=[Depends(require_role("admin", "worker"))],
        response_model=schemas.JobOut,
    )
    def complete_job(
        job_id: str, payload: schemas.JobComplete, db: Session = Depends(get_db)
    ):
        j = crud.complete_job(db, job_id, payload.status, payload.logs)
        if not j:
            raise HTTPException(
                status_code=409, detail="Job not found or not in RUNNING state"
            )
        return _job_out(j)

    @app.patch(
        "/jobs/{job_id}/logs",
        dependencies=[Depends(require_role("admin", "worker"))],
        response_model=schemas.JobLogsOut,
    )
    def append_logs(
        job_id: str, payload: schemas.JobLogsAppend, db: Session = Depends(get_db)
    ):
        j = crud.append_logs(db, job_id, payload.data)
        if not j:
            raise HTTPException(
                status_code=409, detail="Job not found or not in RUNNING state"
            )
        return schemas.JobLogsOut(job_id=j.id, status=j.status, logs=j.logs or "")

    @app.get(
        "/jobs/{job_id}/logs",
        dependencies=[Depends(require_role("admin", "user", "worker"))],
        response_model=schemas.JobLogsOut,
    )
    def get_logs(
        job_id: str,
        offset: int = Query(0, ge=0),
        db: Session = Depends(get_db),
    ):
        j = crud.get_job(db, job_id)
        if not j:
            raise HTTPException(status_code=404, detail="Job not found")
        logs = j.logs or ""
        return schemas.JobLogsOut(job_id=j.id, status=j.status, logs=logs[offset:])

    return app


app = create_app()
