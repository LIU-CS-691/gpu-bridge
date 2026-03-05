from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    status: str = "ok"

class WorkerCreate(BaseModel):
    name: str = Field(default="Unnamed GPU", max_length=200)

class WorkerOut(BaseModel):
    id: str
    name: str

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
