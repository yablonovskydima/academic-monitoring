from pydantic import BaseModel, ConfigDict

class TeacherOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    department: str


class TeacherCreate(BaseModel):
    full_name: str
    department: str

class TeacherUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = None
    department: str | None = None


class TeacherSubjectOfferingShort(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject_id: int
    semester_id: int


class TeacherFull(TeacherOut):
    subject_offerings: list[TeacherSubjectOfferingShort] = []
