from pydantic import BaseModel


class StudentOut(BaseModel):
    id: int
    full_name: str
    group: str
    avg_grade: float
    absence_percent: float