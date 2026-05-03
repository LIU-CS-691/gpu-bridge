from datetime import datetime, timezone

from sqlalchemy.orm import Session

from . import models

VALID_TRANSITIONS = {
    "PENDING": {"RUNNING"},
    "RUNNING": {"SUCCEEDED", "FAILED"},
}


def create_worker(db: Session, name: str) -> models.Worker:
    w = models.Worker(name=name)
    db.add(w)
    db.commit()
    db.refresh(w)
    return w


def get_worker(db: Session, worker_id: str) -> models.Worker | None:
    return db.get(models.Worker, worker_id)


def list_workers(db: Session) -> list[models.Worker]:
    return db.query(models.Worker).order_by(models.Worker.created_at.desc()).all()


def heartbeat(db: Session, worker_id: str) -> models.Worker | None:
    w = db.get(models.Worker, worker_id)
    if not w:
        return None
    w.last_heartbeat = datetime.now(timezone.utc)
    db.commit()
    db.refresh(w)
    return w


def create_job(db: Session, worker_id: str, image: str, command: str) -> models.Job:
    j = models.Job(worker_id=worker_id, image=image, command=command, status="PENDING")
    db.add(j)
    db.commit()
    db.refresh(j)
    return j


def get_job(db: Session, job_id: str) -> models.Job | None:
    return db.get(models.Job, job_id)


def list_jobs(
    db: Session,
    worker_id: str | None = None,
    status: str | None = None,
) -> list[models.Job]:
    q = db.query(models.Job)
    if worker_id:
        q = q.filter(models.Job.worker_id == worker_id)
    if status:
        q = q.filter(models.Job.status == status)
    return q.order_by(models.Job.created_at.desc()).all()


def claim_job(db: Session, job_id: str) -> models.Job | None:
    j = db.get(models.Job, job_id)
    if not j or j.status != "PENDING":
        return None
    j.status = "RUNNING"
    db.commit()
    db.refresh(j)
    return j


def complete_job(
    db: Session, job_id: str, status: str, logs: str | None = None
) -> models.Job | None:
    j = db.get(models.Job, job_id)
    if not j or j.status != "RUNNING":
        return None
    if status not in VALID_TRANSITIONS.get("RUNNING", set()):
        return None
    j.status = status
    if logs:
        j.logs = (j.logs or "") + logs
    db.commit()
    db.refresh(j)
    return j


def append_logs(db: Session, job_id: str, data: str) -> models.Job | None:
    j = db.get(models.Job, job_id)
    if not j or j.status != "RUNNING":
        return None
    j.logs = (j.logs or "") + data
    db.commit()
    db.refresh(j)
    return j
