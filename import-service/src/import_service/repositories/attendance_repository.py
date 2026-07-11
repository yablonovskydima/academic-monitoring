from sqlalchemy import select
from sqlalchemy.orm import Session

from import_service.models.attendance import Attendance


class AttendanceRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self) -> list[Attendance]:
        return list(self.session.scalars(select(Attendance)).all())

    def get_by_id(self, attendance_id: int) -> Attendance | None:
        return self.session.scalars(
            select(Attendance).where(Attendance.id == attendance_id)
        ).first()

    def get_by_student(self, student_id: int) -> list[Attendance]:
        return list(self.session.scalars(
            select(Attendance).where(Attendance.student_id == student_id)
        ).all())

    def get_by_session(self, class_session_id: int) -> list[Attendance]:
        return list(self.session.scalars(
            select(Attendance).where(Attendance.class_session_id == class_session_id)
        ).all())

    def create(self, attendance: Attendance) -> Attendance:
        self.session.add(attendance)
        self.session.commit()
        self.session.refresh(attendance)
        return attendance

    def bulk_create(self, attendances: list[Attendance]) -> None:
        self.session.add_all(attendances)
        self.session.commit()

    def update(self, attendance_id: int, **fields) -> Attendance | None:  # todo dto for update
        attendance = self.get_by_id(attendance_id)
        if attendance is None:
            return None
        for key, value in fields.items():
            setattr(attendance, key, value)
        self.session.commit()
        self.session.refresh(attendance)
        return attendance