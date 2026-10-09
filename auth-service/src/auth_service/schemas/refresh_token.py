from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RefreshTokenCreate(BaseModel):
    user_id: int
    token_hash: str
    expires_at: datetime


class RefreshTokenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    issued_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
