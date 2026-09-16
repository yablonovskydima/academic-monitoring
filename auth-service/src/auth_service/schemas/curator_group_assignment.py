from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssignGroupRequest(BaseModel):
    group_id: int


class CuratorGroupAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    group_id: int
    assigned_at: datetime
