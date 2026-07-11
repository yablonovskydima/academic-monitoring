from pydantic import BaseModel, ConfigDict
from datetime import date

class SemesterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    academic_year: str
    term: int
    start_date: date
    end_date: date

class SemesterCreate(BaseModel):
    academic_year: str
    term: int
    start_date: date
    end_date: date


class SemesterUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    academic_year: str | None = None
    term: int | None = None
    start_date: date | None = None
    end_date: date | None = None
