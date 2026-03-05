from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from . import crud, schemas
from .auth import require_token
from .db import Base, engine, get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: auto-create tables (no migrations yet).
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: cleanup if needed


def create_app() -> FastAPI:
    app = FastAPI(title="GPUBridge Controller", lifespan=lifespan)

    @app.get("/health", response_model=schemas.HealthResponse)
    def health():
        return schemas.HealthResponse(status="ok")

    @app.post("/workers/register", dependencies=[Depends(require_token)], response_model=schemas.WorkerOut)
    def register_worker(payload: schemas.WorkerCreate, db: Session = Depends(get_db)):
        w = crud.create_worker(db, payload.name)
        return schemas.WorkerOut(id=w.id, name=w.name)

    @app.get("/workers", dependencies=[Depends(require_token)], response_model=list[schemas.WorkerOut])
    def workers(db: Session = Depends(get_db)):
        ws = crud.list_workers(db)
        return [schemas.WorkerOut(id=w.id, name=w.name) for w in ws]

    @app.post("/jobs", dependencies=[Depends(require_token)], response_model=schemas.JobOut)
    def create_job(payload: schemas.JobCreate, db: Session = Depends(get_db)):
        # Validate worker exists
        ws = {w.id for w in crud.list_workers(db)}
        if payload.worker_id not in ws:
            raise HTTPException(status_code=404, detail="Worker not found")
        j = crud.create_job(db, payload.worker_id,
                            payload.image, payload.command)
        return schemas.JobOut(id=j.id, worker_id=j.worker_id, image=j.image, command=j.command, status=j.status)

    @app.get("/jobs/{job_id}", dependencies=[Depends(require_token)], response_model=schemas.JobOut)
    def get_job(job_id: str, db: Session = Depends(get_db)):
        j = crud.get_job(db, job_id)
        if not j:
            raise HTTPException(status_code=404, detail="Job not found")
        return schemas.JobOut(id=j.id, worker_id=j.worker_id, image=j.image, command=j.command, status=j.status)

    return app


app = create_app()
