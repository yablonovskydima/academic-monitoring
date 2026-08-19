from datetime import date, datetime

from sqlalchemy.orm import Session

from import_service.database import SessionLocal
from import_service.importer.sources.base import DataSource
from import_service.models.class_session import SessionType
from import_service.schemas.attendance import AttendanceCreate
from import_service.schemas.class_session import ClassSessionCreate
from import_service.schemas.enrollment import EnrollmentCreate
from import_service.schemas.grade import GradeCreate
from import_service.schemas.semester import SemesterCreate
from import_service.schemas.subject import SubjectCreate
from import_service.schemas.subject_offering import SubjectOfferingCreate
from import_service.schemas.teacher import TeacherCreate
from import_service.services.attendance_service import AttendanceService
from import_service.services.class_session_service import ClassSessionService
from import_service.services.enrollment_service import EnrollmentService
from import_service.services.grade_service import GradeService
from import_service.services.group_service import GroupService
from import_service.services.semester_service import SemesterService
from import_service.services.student_service import StudentService
from import_service.importer.utils.chunking import chunked

from import_service.schemas.group import GroupCreate
from import_service.schemas.student import StudentCreate

from import_service.models.student import StudyMode
from import_service.services.subject_offering_service import SubjectOfferingService
from import_service.services.subject_service import SubjectService
from import_service.services.teacher_service import TeacherService

CHUNK_SIZE = 10000

def _build_id_map(rows: list[dict], created: list) -> dict[int, int]:
    return {int(row["id"]): obj.id for row, obj in zip(rows, created)}


def _bulk_import(service, data: list, chunk_size: int = CHUNK_SIZE, label: str = "") -> list:
    created: list = []
    total = len(data)
    for chunk in chunked(data, chunk_size):
        created.extend(service.bulk_create(chunk))
        if label:
            print(f"  {label}: {len(created)}/{total}")
    return created

def import_groups(db: Session, source: DataSource) -> dict[int, int]:
    rows = source.load_groups()
    data = [GroupCreate(name=r["name"], faculty=r["faculty"], course_year=int(r["course_year"])) for r in rows]
    created = _bulk_import(GroupService(db), data, label="groups")
    print(f"Imported {len(created)} groups")
    return _build_id_map(rows, created)


def import_students(db: Session, source: DataSource, group_map: dict[int, int]) -> dict[int, int]:
    rows = source.load_students()
    data = [
        StudentCreate(
            full_name=r["full_name"],
            group_id=group_map[int(r["group_id"])],
            email=r["email"],
            study_mode=StudyMode(r["study_mode"]),
        )
        for r in rows
    ]
    created = _bulk_import(StudentService(db), data, label="students")
    print(f"Imported {len(created)} students")
    return _build_id_map(rows, created)


def import_semesters(db: Session, source: DataSource) -> dict[int, int]:
    rows = source.load_semesters()
    data = [
        SemesterCreate(
            academic_year=r["academic_year"],
            term=int(r["term"]),
            start_date=date.fromisoformat(r["start_date"]),
            end_date=date.fromisoformat(r["end_date"]),
        )
        for r in rows
    ]
    created = _bulk_import(SemesterService(db), data, label="semesters")
    print(f"Imported {len(created)} semesters")
    return _build_id_map(rows, created)


def import_teachers(db: Session, source: DataSource) -> dict[int, int]:
    rows = source.load_teachers()
    data = [TeacherCreate(full_name=r["full_name"], department=r["department"]) for r in rows]
    created = _bulk_import(TeacherService(db), data, label="teachers")
    print(f"Imported {len(created)} teachers")
    return _build_id_map(rows, created)


def import_subjects(db: Session, source: DataSource) -> dict[int, int]:
    rows = source.load_subjects()
    data = [SubjectCreate(name=r["name"], is_elective=r["is_elective"] == "True") for r in rows]
    created = _bulk_import(SubjectService(db), data, label="subjects")
    print(f"Imported {len(created)} subjects")
    return _build_id_map(rows, created)


def import_subject_offerings(
    db: Session, source: DataSource,
    subject_map: dict[int, int], semester_map: dict[int, int], teacher_map: dict[int, int],
) -> dict[int, int]:
    rows = source.load_subject_offerings()
    data = [
        SubjectOfferingCreate(
            subject_id=subject_map[int(r["subject_id"])],
            semester_id=semester_map[int(r["semester_id"])],
            teacher_id=teacher_map[int(r["teacher_id"])],
            max_practice_score=int(r["max_practice_score"]),
            max_exam_score=int(r["max_exam_score"]),
        )
        for r in rows
    ]
    created = _bulk_import(SubjectOfferingService(db), data, label="subject_offerings")
    print(f"Imported {len(created)} subject offerings")
    return _build_id_map(rows, created)


def import_enrollments(
    db: Session, source: DataSource,
    student_map: dict[int, int], offering_map: dict[int, int],
) -> dict[int, int]:
    rows = source.load_enrollments()
    data = [
        EnrollmentCreate(
            student_id=student_map[int(r["student_id"])],
            subject_offering_id=offering_map[int(r["subject_offering_id"])],
        )
        for r in rows
    ]
    created = _bulk_import(EnrollmentService(db), data, label="enrollments")
    print(f"Imported {len(created)} enrollments")
    return _build_id_map(rows, created)


def import_class_sessions(db: Session, source: DataSource, offering_map: dict[int, int]) -> dict[int, int]:
    rows = source.load_class_sessions()
    data = [
        ClassSessionCreate(
            subject_offering_id=offering_map[int(r["subject_offering_id"])],
            session_type=SessionType(r["session_type"]),
            session_number=int(r["session_number"]),
            date=date.fromisoformat(r["date"]),
        )
        for r in rows
    ]
    created = _bulk_import(ClassSessionService(db), data, label="class_sessions")
    print(f"Imported {len(created)} class sessions")
    return _build_id_map(rows, created)


def import_attendance(
    db: Session, source: DataSource,
    student_map: dict[int, int], session_map: dict[int, int],
) -> None:
    rows = source.load_attendance()
    data = [
        AttendanceCreate(
            student_id=student_map[int(r["student_id"])],
            class_session_id=session_map[int(r["class_session_id"])],
            is_absent=r["is_absent"] == "True",
            is_worked_off=r["is_worked_off"] == "True",
            is_excused=r["is_excused"] == "True",
        )
        for r in rows
    ]
    created = _bulk_import(AttendanceService(db), data, label="attendance")
    print(f"Imported {len(created)} attendance rows")


def import_grades(
    db: Session, source: DataSource,
    student_map: dict[int, int], session_map: dict[int, int],
) -> None:
    rows = source.load_grades()
    data = [
        GradeCreate(
            student_id=student_map[int(r["student_id"])],
            class_session_id=session_map[int(r["class_session_id"])],
            score=float(r["score"]),
            deadline_at=datetime.fromisoformat(r["deadline_at"]) if r.get("deadline_at") else None,
            graded_at=datetime.fromisoformat(r["graded_at"]) if r.get("graded_at") else None,
        )
        for r in rows
    ]
    created = _bulk_import(GradeService(db), data, label="grades")
    print(f"Imported {len(created)} grades")


def run_import(source: DataSource):
    db = SessionLocal()
    try:
        group_map = import_groups(db, source)
        student_map = import_students(db, source, group_map)
        semester_map = import_semesters(db, source)
        teacher_map = import_teachers(db, source)
        subject_map = import_subjects(db, source)
        offering_map = import_subject_offerings(db, source, subject_map, semester_map, teacher_map)
        import_enrollments(db, source, student_map, offering_map)
        session_map = import_class_sessions(db, source, offering_map)
        import_attendance(db, source, student_map, session_map)
        import_grades(db, source, student_map, session_map)

        print("\nImport finished successfully.")
    finally:
        db.close()