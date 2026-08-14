from pydantic import BaseModel, ConfigDict
from datetime import date
from import_service.models.class_session import SessionType


class SubjectOfferingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject_id: int
    semester_id: int
    teacher_id: int
    max_practice_score: int
    max_exam_score: int


class SubjectOfferingCreate(BaseModel):
    subject_id: int
    semester_id: int
    teacher_id: int
    max_practice_score: int = 50
    max_exam_score: int = 50


class SubjectOfferingUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_id: int | None = None
    semester_id: int | None = None
    teacher_id: int | None = None
    max_practice_score: int | None = None
    max_exam_score: int | None = None


class SubjectClassSessionShort(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_type: SessionType
    session_number: int
    date: date


class SubjectEnrolledStudentShort(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: int


class SubjectOfferingFull(SubjectOfferingOut):
    class_sessions: list[SubjectClassSessionShort] = []
    enrollments: list[SubjectClassSessionShort] = []