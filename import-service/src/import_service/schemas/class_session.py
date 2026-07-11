from pydantic import BaseModel, ConfigDict
from datetime import date as date_type
from import_service.models.class_session import SessionType


class ClassSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject_offering_id: int
    session_type: SessionType
    session_number: int
    date: date_type


class ClassSessionCreate(BaseModel):
    subject_offering_id: int
    session_type: SessionType
    session_number: int
    date: date_type


class ClassSessionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_offering_id: int | None = None
    session_type: SessionType | None = None
    session_number: int | None = None
    date: date_type | None = None


class AttendanceShort(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    is_absent: bool
    is_worked_off: bool
    is_excused: bool


class GradeShort(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    score: float
    deadline_at: str | None = None
    graded_at: str | None = None


class ClassSessionFull(ClassSessionOut):
    attendances: list[AttendanceShort] = []
    grades: list[GradeShort] = []