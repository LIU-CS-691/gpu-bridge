import uuid
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from .db import Base

def _uuid() -> str:
    return uuid.uuid4().hex

class Worker(Base):
    __tablename__ = "workers"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), default="Unnamed GPU")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    jobs: Mapped[list["Job"]] = relationship(back_populates="worker")

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    worker_id: Mapped[str] = mapped_column(String(32), ForeignKey("workers.id"), index=True)
    image: Mapped[str] = mapped_column(String(400), default="hello-image")
    command: Mapped[str] = mapped_column(String(1000), default="echo hello")
    status: Mapped[str] = mapped_column(String(32), default="PENDING")  # PENDING/RUNNING/SUCCEEDED/FAILED
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    worker: Mapped["Worker"] = relationship(back_populates="jobs")
