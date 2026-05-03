from typing import Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class GpuDevice(BaseModel):
    index: int
    name: str
    memory_total_mb: int
    memory_free_mb: int
    utilization_pct: int


class WorkerCreate(BaseModel):
    name: str = Field(default="Unnamed GPU", max_length=200)
    gpu_info: Optional[list[GpuDevice]] = None


class WorkerOut(BaseModel):
    id: str
    name: str
    last_heartbeat: Optional[str] = None
    status: str = "unknown"
    gpu_info: Optional[list[GpuDevice]] = None


class WorkerHeartbeat(BaseModel):
    gpu_info: Optional[list[GpuDevice]] = None


class JobCreate(BaseModel):
    worker_id: Optional[str] = None
    image: str = "hello-image"
    command: str = "echo hello"
    priority: int = Field(default=0, ge=0, le=10)


class JobOut(BaseModel):
    id: str
    worker_id: Optional[str] = None
    image: str
    command: str
    status: str
    priority: int = 0
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
