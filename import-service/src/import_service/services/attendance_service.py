from sqlalchemy.orm import Session

from import_service.models.attendance import Attendance
from import_service.repositories.attendance_repository import AttendanceRepository
from import_service.schemas.attendance import AttendanceCreate, AttendanceUpdate


class AttendanceService:
    def __init__(self, db: Session):
        self.repo = AttendanceRepository(db)

    def get_by_id(self, attendance_id: int) -> Attendance | None:
        return self.repo.get_by_id(attendance_id)

    def get_by_student(self, student_id: int) -> list[Attendance]:
        return self.repo.get_by_student(student_id)

    def get_by_session(self, class_session_id: int) -> list[Attendance]:
        return self.repo.get_by_session(class_session_id)

    def create(self, data: AttendanceCreate) -> Attendance:
        attendance = Attendance(**data.model_dump())
        return self.repo.save(attendance)

    def bulk_create(self, items_data: list[AttendanceCreate]) -> list[Attendance]:
        attendances = [Attendance(**data.model_dump()) for data in items_data]
        return self.repo.bulk_save(attendances)

    def update(self, attendance_id: int, data: AttendanceUpdate) -> Attendance | None:
        attendance = self.repo.get_by_id(attendance_id)
        if attendance is None:
            return None

        update_fields = data.model_dump(exclude_unset=True)
        for key, value in update_fields.items():
            setattr(attendance, key, value)

        return self.repo.save(attendance)

    def delete(self, attendance_id: int) -> bool:
        return self.repo.delete(attendance_id)