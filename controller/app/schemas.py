from typing import Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class WorkerCreate(BaseModel):
    name: str = Field(default="Unnamed GPU", max_length=200)


class WorkerOut(BaseModel):
    id: str
    name: str
    last_heartbeat: Optional[str] = None
    status: str = "unknown"


class JobCreate(BaseModel):
    worker_id: str
    image: str = "hello-image"
    command: str = "echo hello"


class JobOut(BaseModel):
    id: str
    worker_id: str
    image: str
    command: str
    status: str
    logs: Optional[str] = None


class JobComplete(BaseModel):
    status: str = Field(..., pattern="^(SUCCEEDED|FAILED)$")
    logs: Optional[str] = None


class JobLogsAppend(BaseModel):
    data: str


class JobLogsOut(BaseModel):
    job_id: str
    status: str
    logs: str
