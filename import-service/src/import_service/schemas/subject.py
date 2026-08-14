from pydantic import BaseModel, ConfigDict


class SubjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_elective: bool = False


class SubjectCreate(BaseModel):
    name: str
    is_elective: bool = False


class SubjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    is_elective: bool | None = None