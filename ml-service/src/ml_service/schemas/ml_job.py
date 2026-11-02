from datetime import datetime

from pydantic import BaseModel, ConfigDict

from ml_service.models.ml_job import MLJobStatus, MLJobType


class MLJobCreate(BaseModel):
    requested_by: int | None = None


class MLJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_type: MLJobType
    status: MLJobStatus
    requested_by: int | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    result: dict | None
    error: str | None
