from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from import_service.models.student import Student


class StudentRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self) -> list[Student]:
        return list(self.session.scalars(select(Student)).all())

    def get_by_id(self, student_id: int) -> Student | None:
        return self.session.scalars(
            select(Student).where(Student.id == student_id)
        ).first()

    def get_by_group(self, group_id: int) -> list[Student]:
        return list(self.session.scalars(
            select(Student).where(Student.group_id == group_id)
        ).all())

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

    def save(self, student: Student) -> Student:
        self.session.add(student)
        self.session.commit()
        self.session.refresh(student)
        return student

    def bulk_save(self, students: list[Student]) -> None:
        self.session.add_all(students)
        self.session.commit()

    def delete(self, student_id: int) -> bool:
        student = self.get_by_id(student_id)
        if student is None:
            return False
        self.session.delete(student)
        self.session.commit()
        return True

    #TODO зробити такі ж репо для всього