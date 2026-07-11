from pydantic import BaseModel, ConfigDict
from datetime import datetime
from import_service.models.student import StudyMode


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    group_id: int
    email: str
    study_mode: StudyMode
    created_at: datetime
    

class StudentCreate(BaseModel):
    full_name: str
    group_id: int
    email: str
    study_mode: StudyMode


class StudentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = None
    group_id: int | None = None
    email: str | None = None
    study_mode: StudyMode | None = None


class StudentGradeShort(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    class_session_id: int
    score: float
    deadline_at: datetime | None
    graded_at: datetime | None


class StudentAttendanceShort(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    class_session_id: int
    is_absent: bool
    is_worked_off: bool
    is_excused: bool


class EnrollmentShort(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject_offering_id: int
    enrolled_at: datetime


class StudentFull(StudentOut):
    grades: list[StudentGradeShort] = []
    attendances: list[StudentAttendanceShort] = []
    enrollments: list[EnrollmentShort] = []