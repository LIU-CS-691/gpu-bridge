import uuid
from typing import Optional

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


class Worker(Base):
    __tablename__ = "workers"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), default="Unnamed GPU")
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_heartbeat: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    jobs: Mapped[list["Job"]] = relationship(back_populates="worker")


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    worker_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("workers.id"), index=True
    )
    image: Mapped[str] = mapped_column(String(400), default="hello-image")
    command: Mapped[str] = mapped_column(String(1000), default="echo hello")
    status: Mapped[str] = mapped_column(String(32), default="PENDING")
    logs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    worker: Mapped["Worker"] = relationship(back_populates="jobs")
