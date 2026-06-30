from fastapi import APIRouter

from import_service.schemas.student import StudentOut

router = APIRouter(prefix="/students", tags=["students"])

_FAKE_STUDENTS = [
    StudentOut(id=1, full_name="Іван Петренко", group="КН-21", avg_grade=87.5, absence_percent=12.0),
    StudentOut(id=2, full_name="Олена Коваль", group="КН-21", avg_grade=63.2, absence_percent=41.0),
]


@router.get("/", response_model=list[StudentOut])
def get_students():
    return _FAKE_STUDENTS


@router.get("/{student_id}", response_model=StudentOut)
def get_student(student_id: int):
    for student in _FAKE_STUDENTS:
        if student.id == student_id:
            return student
    return {"error": "not found"}