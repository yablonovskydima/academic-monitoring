import secrets
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.orm import Session

from auth_service.config import REFRESH_TOKEN_EXPIRE_DAYS
from auth_service.models.refresh_token import RefreshToken
from auth_service.repositories.refresh_token_repository import RefreshTokenRepository
from auth_service.utils.clock import utc_now
from auth_service.utils.security import hash_token


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
            expires_at=utc_now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        )
        self.repo.save(record)

        return IssuedToken(raw_token=raw_token, record=record)

    def get_valid(self, raw_token: str) -> RefreshToken | None:
        record = self.repo.get_by_hash(hash_token(raw_token))
        return record if self._is_usable(record) else None

    def is_session_active(self, session_id: int, user_id: int) -> bool:
        record = self.repo.get_by_id(session_id)
        return self._is_usable(record) and record.user_id == user_id

    @staticmethod
    def _is_usable(record: RefreshToken | None) -> bool:
        if record is None:
            return False
        if record.revoked_at is not None:
            return False
        return record.expires_at >= utc_now()

    def revoke(self, raw_token: str) -> bool:
        record = self.repo.get_by_hash(hash_token(raw_token))
        if record is None:
            return False
        return self.repo.revoke(record.id)

    def revoke_all_for_user(self, user_id: int) -> None:
        self.repo.revoke_all_for_user(user_id)
