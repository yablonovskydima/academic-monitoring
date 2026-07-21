from pydantic import BaseModel, ConfigDict

class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    faculty: str
    course_year: int

class GroupCreate(BaseModel):
    name: str
    faculty: str
    course_year: int


class GroupUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    faculty: str | None = None
    course_year: int | None = None


class GroupStudentShort(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str


class GroupFull(GroupOut):
    students: list[GroupStudentShort] = []