import enum
from datetime import datetime

from sqlalchemy import JSON, Enum as SAEnum, Index, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from ml_service.database import Base


class MLJobType(str, enum.Enum):
    training = "training"
    inference = "inference"


class MLJobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


ACTIVE_JOB_STATUSES = (MLJobStatus.queued, MLJobStatus.running)
_ACTIVE_CONDITION = text("status IN ('queued', 'running')")


class MLJob(Base):
    __tablename__ = "ml_jobs"
    __table_args__ = (
        Index(
            "uq_ml_jobs_one_active_per_type",
            "job_type",
            unique=True,
            postgresql_where=_ACTIVE_CONDITION,
            sqlite_where=_ACTIVE_CONDITION,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_type: Mapped[MLJobType] = mapped_column(SAEnum(MLJobType, name="ml_job_type_enum"), index=True)
    status: Mapped[MLJobStatus] = mapped_column(SAEnum(MLJobStatus, name="ml_job_status_enum"))
    requested_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime]
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
