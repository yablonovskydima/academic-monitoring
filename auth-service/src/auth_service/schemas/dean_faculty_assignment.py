from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DeanFacultyAssignmentCreate(BaseModel):
    user_id: int
    faculty_id: int


class DeanFacultyAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    faculty_id: int
    assigned_at: datetime
