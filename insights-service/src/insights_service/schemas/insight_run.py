from datetime import datetime

from pydantic import BaseModel, ConfigDict


class InsightRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_job_id: int | None
    semester_id: int
    students_count: int
    created_at: datetime
