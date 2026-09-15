import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from auth_service.config import REFRESH_TOKEN_EXPIRE_DAYS
from auth_service.models.refresh_token import RefreshToken
from auth_service.repositories.refresh_token_repository import RefreshTokenRepository
from auth_service.security import hash_token


@dataclass
class IssuedToken:
    raw_token: str
    record: RefreshToken


class RefreshTokenService:
    def __init__(self, db: Session):
        self.repo = RefreshTokenRepository(db)

    def issue(self, user_id: int) -> IssuedToken:
        raw_token = secrets.token_urlsafe(48)

        record = RefreshToken(
            user_id=user_id,
            token_hash=hash_token(raw_token),
            expires_at=datetime.now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        )
        self.repo.save(record)

        return IssuedToken(raw_token=raw_token, record=record)

    def get_valid(self, raw_token: str) -> RefreshToken | None:
        record = self.repo.get_by_hash(hash_token(raw_token))
        if record is None:
            return None
        if record.revoked_at is not None:
            return None
        if record.expires_at < datetime.utcnow():
            return None
        return record

    def revoke(self, raw_token: str) -> bool:
        record = self.repo.get_by_hash(hash_token(raw_token))
        if record is None:
            return False
        return self.repo.revoke(record.id)

    def revoke_all_for_user(self, user_id: int) -> None:
        self.repo.revoke_all_for_user(user_id)
