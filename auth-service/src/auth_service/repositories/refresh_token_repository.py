from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from auth_service.models.refresh_token import RefreshToken
from auth_service.utils.clock import utc_now


class RefreshTokenRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.session.scalars(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        ).first()

    def get_by_id(self, token_id: int) -> RefreshToken | None:
        return self.session.get(RefreshToken, token_id)

    def save(self, token: RefreshToken) -> RefreshToken:
        self.session.add(token)
        self.session.flush()
        self.session.commit()
        return token

    def revoke(self, token_id: int) -> bool:
        token = self.session.get(RefreshToken, token_id)
        if token is None:
            return False
        token.revoked_at = utc_now()
        self.session.commit()
        return True

    def revoke_all_for_user(self, user_id: int) -> None:
        tokens = self.session.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
        ).all()
        for token in tokens:
            token.revoked_at = utc_now()
        self.session.commit()

    def delete_all_for_user(self, user_id: int) -> None:
        self.session.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
        self.session.commit()
