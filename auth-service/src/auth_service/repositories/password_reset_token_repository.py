from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from auth_service.models.password_reset_token import PasswordResetToken


class PasswordResetTokenRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        return self.session.scalars(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        ).first()

    def save(self, token: PasswordResetToken) -> PasswordResetToken:
        self.session.add(token)
        self.session.flush()
        self.session.commit()
        return token

    def mark_used(self, token_id: int) -> bool:
        token = self.session.get(PasswordResetToken, token_id)
        if token is None:
            return False
        token.used_at = datetime.utcnow()
        self.session.commit()
        return True
