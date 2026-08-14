from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from import_service.database import get_db
from import_service.services.student_service import StudentService
from import_service.schemas.student import StudentOut, StudentFull

router = APIRouter(prefix="/students", tags=["students"])


@router.get("/", response_model=list[StudentOut])
def get_students(db: Session = Depends(get_db)):
    return StudentService(db).get_all()


@router.get("/{student_id}", response_model=StudentOut)
def get_student(student_id: int, db: Session = Depends(get_db)):
    student = StudentService(db).get_by_id(student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.get("/{student_id}/full", response_model=StudentFull)
def get_student_full(student_id: int, db: Session = Depends(get_db)):
    student = StudentService(db).get_full(student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.get("/by-group/{group_id}", response_model=list[StudentOut])
def get_students_by_group(group_id: int, db: Session = Depends(get_db)):
    return StudentService(db).get_by_group(group_id)