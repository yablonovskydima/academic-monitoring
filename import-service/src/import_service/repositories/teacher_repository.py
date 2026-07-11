from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from import_service.models.teacher import Teacher


class TeacherRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_full_by_id(self, teacher_id: int) -> Teacher | None:
        return self.session.scalars(
            select(Teacher)
            .options(joinedload(Teacher.subject_offerings))
            .where(Teacher.id == teacher_id)
        ).unique().first()

    def get_all(self) -> list[Teacher]:
        return list(self.session.scalars(select(Teacher)).all())

    def get_by_id(self, teacher_id: int) -> Teacher | None:
        return self.session.scalars(
            select(Teacher).where(Teacher.id == teacher_id)
        ).first()

    def create(self, teacher: Teacher) -> Teacher:
        self.session.add(teacher)
        self.session.commit()
        self.session.refresh(teacher)
        return teacher

    def bulk_create(self, teachers: list[Teacher]) -> None:
        self.session.add_all(teachers)
        self.session.commit()

    def update(self, teacher_id: int, **fields) -> Teacher | None:  # todo dto for update
        teacher = self.get_by_id(teacher_id)
        if teacher is None:
            return None
        for key, value in fields.items():
            setattr(teacher, key, value)
        self.session.commit()
        self.session.refresh(teacher)
        return teacher