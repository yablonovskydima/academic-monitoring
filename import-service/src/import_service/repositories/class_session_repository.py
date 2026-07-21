from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from import_service.models.class_session import ClassSession


class ClassSessionRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, session_id: int) -> ClassSession | None:
        return self.session.scalars(
            select(ClassSession).where(ClassSession.id == session_id)
        ).first()

    def get_by_offering(self, subject_offering_id: int) -> list[ClassSession]:
        return list(self.session.scalars(
            select(ClassSession)
            .where(ClassSession.subject_offering_id == subject_offering_id)
            .order_by(ClassSession.date)
        ).all())

    def get_full_by_id(self, session_id: int) -> ClassSession | None:
        return self.session.scalars(
            select(ClassSession)
            .options(
                joinedload(ClassSession.attendances),
                joinedload(ClassSession.grades),
            )
            .where(ClassSession.id == session_id)
        ).unique().first()

    def save(self, class_session: ClassSession) -> ClassSession:
        self.session.add(class_session)
        self.session.commit()
        self.session.refresh(class_session)
        return class_session

    def bulk_save(self, class_sessions: list[ClassSession]) -> None:
        self.session.add_all(class_sessions)
        self.session.commit()

    def delete(self, session_id: int) -> bool:
        class_session = self.get_by_id(session_id)
        if class_session is None:
            return False
        self.session.delete(class_session)
        self.session.commit()
        return True