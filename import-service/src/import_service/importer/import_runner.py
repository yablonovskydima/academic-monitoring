from sqlalchemy.orm import Session

from import_service.database import SessionLocal
from import_service.importer.sources.base import DataSource
from import_service.services.group_service import GroupService
from import_service.services.student_service import StudentService

from import_service.schemas.group import GroupCreate
from import_service.schemas.student import StudentCreate

from import_service.models.student import StudyMode


def import_groups(db: Session, source: DataSource) -> dict[int, int]:
    service = GroupService(db)
    rows = source.load_groups()

    id_map = {}
    for row in rows:
        group = service.create(GroupCreate(
            name=row["name"],
            faculty=row["faculty"],
            course_year=int(row["course_year"]),
        ))
        id_map[int(row["id"])] = group.id

    print(f"Imported {len(id_map)} groups")
    return id_map


def import_students(db: Session, source: DataSource, group_id_map: dict[int, int]) -> dict[int, int]:
    service = StudentService(db)
    rows = source.load_students()

    id_map = {}
    for row in rows:
        real_group_id = group_id_map[int(row["group_id"])]

        student = service.create(StudentCreate(
            full_name=row["full_name"],
            group_id=real_group_id,
            email=row["email"],
            study_mode=StudyMode(row["study_mode"]),
        ))
        id_map[int(row["id"])] = student.id

    print(f"Imported {len(id_map)} students")
    return id_map


def run_import(source: DataSource):
    db = SessionLocal()
    try:
        group_id_map = import_groups(db, source)
        import_students(db, source, group_id_map)
        print("Import finished successfully.")
    finally:
        db.close()