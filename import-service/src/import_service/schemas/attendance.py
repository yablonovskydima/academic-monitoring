from pydantic import BaseModel, ConfigDict

class AttendanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    class_session_id: int
    is_absent: bool
    is_worked_off: bool
    is_excused: bool


class AttendanceCreate(BaseModel):
    student_id: int
    class_session_id: int
    is_absent: bool = False
    is_worked_off: bool = False
    is_excused: bool = False


class AttendanceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_absent: bool | None = None
    is_worked_off: bool | None = None
    is_excused: bool | None = None