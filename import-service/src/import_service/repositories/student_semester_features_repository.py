from sqlalchemy import select, func, case
from sqlalchemy.orm import Session

from import_service.models.student import Student
from import_service.models.group import Group
from import_service.models.grade import Grade
from import_service.models.attendance import Attendance
from import_service.models.class_session import ClassSession, SessionType
from import_service.models.subject_offering import SubjectOffering
from import_service.models.semester import Semester
from import_service.models.enrollment import Enrollment


class StudentSemesterFeaturesRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_student_ids_page(self, limit: int, offset: int) -> list[int]:
        query = (
            select(Student.id)
            .order_by(Student.id)
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(query))

    def get_base_info(self, student_ids: list[int]) -> list[dict]:
        query = (
            select(
                Student.id.label("student_id"),
                Student.study_mode,
                Group.course_year,
            )
            .join(Group, Group.id == Student.group_id)
            .where(Student.id.in_(student_ids))
        )
        return [dict(row._mapping) for row in self.session.execute(query)]

    def get_all_semesters(self) -> list[dict]:
        query = select(
            Semester.id.label("semester_id"),
            Semester.academic_year,
            Semester.term,
            Semester.start_date,
        ).order_by(Semester.start_date)
        return [dict(row._mapping) for row in self.session.execute(query)]

    def get_grade_stats_by_semester(self, student_ids: list[int]) -> list[dict]:
        query = (
            select(
                Grade.student_id,
                Semester.id.label("semester_id"),
                func.avg(Grade.score).label("avg_grade"),
                func.stddev(Grade.score).label("grade_stddev"),
            )
            .join(ClassSession, ClassSession.id == Grade.class_session_id)
            .join(SubjectOffering, SubjectOffering.id == ClassSession.subject_offering_id)
            .join(Semester, Semester.id == SubjectOffering.semester_id)
            .where(Grade.student_id.in_(student_ids))
            .group_by(Grade.student_id, Semester.id)
        )
        return [dict(row._mapping) for row in self.session.execute(query)]

    def get_late_submissions_by_semester(self, student_ids: list[int]) -> list[dict]:
        query = (
            select(
                Grade.student_id,
                Semester.id.label("semester_id"),
                func.count(Grade.id).label("late_submissions_count"),
            )
            .join(ClassSession, ClassSession.id == Grade.class_session_id)
            .join(SubjectOffering, SubjectOffering.id == ClassSession.subject_offering_id)
            .join(Semester, Semester.id == SubjectOffering.semester_id)
            .where(Grade.student_id.in_(student_ids))
            .where(Grade.graded_at.is_not(None), Grade.deadline_at.is_not(None))
            .where(Grade.graded_at > Grade.deadline_at)
            .group_by(Grade.student_id, Semester.id)
        )
        return [dict(row._mapping) for row in self.session.execute(query)]

    def get_attendance_stats_by_semester(self, student_ids: list[int]) -> list[dict]:
        query = (
            select(
                Attendance.student_id,
                Semester.id.label("semester_id"),
                func.count(Attendance.id).label("total_sessions"),
                func.sum(case((Attendance.is_absent.is_(True), 1), else_=0)).label("absences_count"),
                func.sum(
                    case(
                        (Attendance.is_absent.is_(True), case((Attendance.is_worked_off.is_(False), 1), else_=0)),
                        else_=0,
                    )
                ).label("unworked_absences_count"),
            )
            .join(ClassSession, ClassSession.id == Attendance.class_session_id)
            .join(SubjectOffering, SubjectOffering.id == ClassSession.subject_offering_id)
            .join(Semester, Semester.id == SubjectOffering.semester_id)
            .where(Attendance.student_id.in_(student_ids))
            .group_by(Attendance.student_id, Semester.id)
        )
        return [dict(row._mapping) for row in self.session.execute(query)]

    def get_attendance_by_session_type_and_semester(self, student_ids: list[int], session_type: SessionType) -> list[dict]:
        query = (
            select(
                Attendance.student_id,
                Semester.id.label("semester_id"),
                func.count(Attendance.id).label("total"),
                func.sum(case((Attendance.is_absent.is_(True), 1), else_=0)).label("absences"),
            )
            .join(ClassSession, ClassSession.id == Attendance.class_session_id)
            .join(SubjectOffering, SubjectOffering.id == ClassSession.subject_offering_id)
            .join(Semester, Semester.id == SubjectOffering.semester_id)
            .where(Attendance.student_id.in_(student_ids))
            .where(ClassSession.session_type == session_type)
            .group_by(Attendance.student_id, Semester.id)
        )
        return [dict(row._mapping) for row in self.session.execute(query)]

    def get_expected_gradable_sessions_by_semester(self, student_ids: list[int]) -> list[dict]:
        query = (
            select(
                Enrollment.student_id,
                Semester.id.label("semester_id"),
                func.count(ClassSession.id).label("total_gradable_sessions"),
            )
            .join(SubjectOffering, SubjectOffering.id == Enrollment.subject_offering_id)
            .join(Semester, Semester.id == SubjectOffering.semester_id)
            .join(ClassSession, ClassSession.subject_offering_id == Enrollment.subject_offering_id)
            .where(Enrollment.student_id.in_(student_ids))
            .where(ClassSession.session_type.in_([SessionType.lab, SessionType.control]))
            .group_by(Enrollment.student_id, Semester.id)
        )
        return [dict(row._mapping) for row in self.session.execute(query)]

    def get_graded_sessions_count_by_semester(self, student_ids: list[int]) -> list[dict]:
        query = (
            select(
                Grade.student_id,
                Semester.id.label("semester_id"),
                func.count(func.distinct(Grade.class_session_id)).label("graded_sessions_count"),
            )
            .join(ClassSession, ClassSession.id == Grade.class_session_id)
            .join(SubjectOffering, SubjectOffering.id == ClassSession.subject_offering_id)
            .join(Semester, Semester.id == SubjectOffering.semester_id)
            .where(Grade.student_id.in_(student_ids))
            .where(ClassSession.session_type.in_([SessionType.lab, SessionType.control]))
            .group_by(Grade.student_id, Semester.id)
        )
        return [dict(row._mapping) for row in self.session.execute(query)]

    def get_enrollments_by_semester(self, student_ids: list[int]) -> list[dict]:
        query = (
            select(
                Enrollment.student_id,
                Semester.id.label("semester_id"),
                SubjectOffering.subject_id,
            )
            .join(SubjectOffering, SubjectOffering.id == Enrollment.subject_offering_id)
            .join(Semester, Semester.id == SubjectOffering.semester_id)
            .where(Enrollment.student_id.in_(student_ids))
        )
        return [dict(row._mapping) for row in self.session.execute(query)]