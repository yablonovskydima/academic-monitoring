from pydantic import BaseModel, ConfigDict
from datetime import datetime


class EnrollmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    subject_offering_id: int
    enrolled_at: datetime


class EnrollmentCreate(BaseModel):
    student_id: int
    subject_offering_id: int


class EnrollmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_offering_id: int | None = None

