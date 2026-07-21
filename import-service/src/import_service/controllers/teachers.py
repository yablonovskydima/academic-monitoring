from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from import_service.database import get_db
from import_service.services.teacher_service import TeacherService
from import_service.schemas.teacher import TeacherOut, TeacherFull

router = APIRouter(prefix="/teachers", tags=["teachers"])


@router.get("/", response_model=list[TeacherOut])
def get_teachers(db: Session = Depends(get_db)):
    return TeacherService(db).get_all()


@router.get("/{teacher_id}", response_model=TeacherOut)
def get_teacher(teacher_id: int, db: Session = Depends(get_db)):
    teacher = TeacherService(db).get_by_id(teacher_id)
    if teacher is None:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return teacher


@router.get("/{teacher_id}/full", response_model=TeacherFull)
def get_teacher_full(teacher_id: int, db: Session = Depends(get_db)):
    teacher = TeacherService(db).get_full(teacher_id)
    if teacher is None:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return teacher