from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogCreate(BaseModel):
    user_id: int | None = None
    action: str
    target_type: str | None = None
    target_id: int | None = None
    details: dict | None = None


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    action: str
    target_type: str | None
    target_id: int | None
    details: dict | None
    created_at: datetime
