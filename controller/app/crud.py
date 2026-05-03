from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from . import models

HEARTBEAT_STALE_SECONDS = 60

VALID_TRANSITIONS = {
    "QUEUED": {"PENDING"},
    "PENDING": {"RUNNING"},
    "RUNNING": {"SUCCEEDED", "FAILED"},
}


def create_worker(
    db: Session, name: str, gpu_info: list[dict] | None = None
) -> models.Worker:
    w = models.Worker(name=name, gpu_info=gpu_info)
    db.add(w)
    db.commit()
    db.refresh(w)
    return w


def get_worker(db: Session, worker_id: str) -> models.Worker | None:
    return db.get(models.Worker, worker_id)


def list_workers(db: Session) -> list[models.Worker]:
    return db.query(models.Worker).order_by(models.Worker.created_at.desc()).all()


def _is_worker_online(w: models.Worker) -> bool:
    if not w.last_heartbeat:
        return False
    age = datetime.now(timezone.utc) - w.last_heartbeat.replace(tzinfo=timezone.utc)
    return age < timedelta(seconds=HEARTBEAT_STALE_SECONDS)


def get_online_workers(db: Session) -> list[models.Worker]:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=HEARTBEAT_STALE_SECONDS)
    return db.query(models.Worker).filter(models.Worker.last_heartbeat >= cutoff).all()


def heartbeat(
    db: Session, worker_id: str, gpu_info: list[dict] | None = None
) -> models.Worker | None:
    w = db.get(models.Worker, worker_id)
    if not w:
        return None
    w.last_heartbeat = datetime.now(timezone.utc)
    if gpu_info is not None:
        w.gpu_info = gpu_info
    db.commit()
    db.refresh(w)
    return w


def _pick_worker(db: Session) -> models.Worker | None:
    """Pick the best online worker: fewest PENDING+RUNNING jobs, prefer workers with GPUs."""
    online = get_online_workers(db)
    if not online:
        return None

    def _score(w: models.Worker) -> tuple[int, int]:
        active = (
            db.query(models.Job)
            .filter(
                models.Job.worker_id == w.id,
                models.Job.status.in_(["PENDING", "RUNNING"]),
            )
            .count()
        )
        has_gpu = 1 if w.gpu_info else 0
        return (-has_gpu, active)

    return min(online, key=_score)


def assign_queued_jobs(db: Session) -> list[models.Job]:
    """Assign QUEUED jobs to available workers, highest priority first."""
    queued = (
        db.query(models.Job)
        .filter(models.Job.status == "QUEUED")
        .order_by(models.Job.priority.desc(), models.Job.created_at.asc())
        .all()
    )

    assigned = []
    for job in queued:
        worker = _pick_worker(db)
        if not worker:
            break
        job.worker_id = worker.id
        job.status = "PENDING"
        assigned.append(job)

    if assigned:
        db.commit()
        for j in assigned:
            db.refresh(j)

    return assigned


def create_job(
    db: Session,
    image: str,
    command: str,
    priority: int = 0,
    worker_id: str | None = None,
) -> models.Job:
    if worker_id:
        j = models.Job(
            worker_id=worker_id,
            image=image,
            command=command,
            priority=priority,
            status="PENDING",
        )
    else:
        j = models.Job(
            image=image,
            command=command,
            priority=priority,
            status="QUEUED",
        )
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
    return q.order_by(models.Job.priority.desc(), models.Job.created_at.desc()).all()


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
