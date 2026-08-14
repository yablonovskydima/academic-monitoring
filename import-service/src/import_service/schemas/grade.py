from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class GradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    class_session_id: int
    score: float
    deadline_at: datetime | None
    graded_at: datetime | None


class GradeCreate(BaseModel):
    student_id: int
    class_session_id: int
    score: float = Field(ge=0, le=100)
    deadline_at: datetime | None = None
    graded_at: datetime | None = None


class GradeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: float | None = Field(default=None, ge=0, le=100)
    deadline_at: datetime | None = None
    graded_at: datetime | None = None