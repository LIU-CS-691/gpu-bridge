from sqlalchemy.orm import Session
from . import models

def create_worker(db: Session, name: str) -> models.Worker:
    w = models.Worker(name=name)
    db.add(w)
    db.commit()
    db.refresh(w)
    return w

def list_workers(db: Session) -> list[models.Worker]:
    return db.query(models.Worker).order_by(models.Worker.created_at.desc()).all()

def create_job(db: Session, worker_id: str, image: str, command: str) -> models.Job:
    j = models.Job(worker_id=worker_id, image=image, command=command, status="PENDING")
    db.add(j)
    db.commit()
    db.refresh(j)
    return j

def get_job(db: Session, job_id: str) -> models.Job | None:
    return db.get(models.Job, job_id)
