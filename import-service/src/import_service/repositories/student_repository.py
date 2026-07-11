from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from import_service.models.student import Student


class StudentRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_full_by_id(self, student_id: int) -> Student | None:
        return self.session.scalars(
            select(Student)
            .options(
                joinedload(Student.grades),
                joinedload(Student.attendances),
                joinedload(Student.enrollments),
            )
            .where(Student.id == student_id)
        ).unique().first()

    def get_all(self) -> list[Student]:
        return list(self.session.scalars(select(Student)).all())

    def get_by_id(self, student_id: int) -> Student | None:
        return self.session.scalars(
            select(Student).where(Student.id == student_id)
        ).first()

    def create(self, student: Student) -> Student:
        self.session.add(student)
        self.session.commit()
        self.session.refresh(student)
        return student

    def bulk_create(self, students: list[Student]) -> None:
        self.session.add_all(students)
        self.session.commit()

    def update(self, student_id: int, **fields) -> Student | None: #todo dto for update
        student = self.get_by_id(student_id)
        if student is None:
            return None
        for key, value in fields.items():
            setattr(student, key, value)
        self.session.commit()
        self.session.refresh(student)
        return student