from pydantic import BaseModel, ConfigDict


class FacultyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class FacultyCreate(BaseModel):
    name: str


class FacultyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None


class FacultyGroupShort(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    course_year: int


class FacultyFull(FacultyOut):
    groups: list[FacultyGroupShort] = []
