import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from auth_service.config import PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
from auth_service.models.password_reset_token import PasswordResetToken
from auth_service.repositories.password_reset_token_repository import PasswordResetTokenRepository
from auth_service.security import hash_token


@dataclass
class IssuedResetToken:
    raw_token: str
    record: PasswordResetToken


class PasswordResetTokenService:
    def __init__(self, db: Session):
        self.repo = PasswordResetTokenRepository(db)

    def issue(self, user_id: int) -> IssuedResetToken:
        raw_token = secrets.token_urlsafe(32)

        record = PasswordResetToken(
            user_id=user_id,
            token_hash=hash_token(raw_token),
            expires_at=datetime.utcnow() + timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
        )
        self.repo.save(record)

        return IssuedResetToken(raw_token=raw_token, record=record)

    def get_valid(self, raw_token: str) -> PasswordResetToken | None:
        record = self.repo.get_by_hash(hash_token(raw_token))
        if record is None:
            return None
        if record.used_at is not None:
            return None
        if record.expires_at < datetime.utcnow():
            return None
        return record

    def mark_used(self, record_id: int) -> bool:
        return self.repo.mark_used(record_id)
