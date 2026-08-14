from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ml_service.database import get_db
from ml_service.services.student_index_service import StudentIndexService
from ml_service.schemas.student_index import StudentIndexOut, StudentIndexFull

router = APIRouter(prefix="/student-indexes", tags=["student_indexes"])


@router.get("/{student_id}/latest", response_model=StudentIndexOut)
def get_latest_index(student_id: int, db: Session = Depends(get_db)):
    result = StudentIndexService(db).get_latest_for_student(student_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No index found for this student")
    return result


@router.get("/{student_id}/latest/full", response_model=StudentIndexFull)
def get_latest_index_full(student_id: int, db: Session = Depends(get_db)):
    result = StudentIndexService(db).get_latest_for_student_full(student_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No index found for this student")
    return result


@router.get("/{student_id}/history", response_model=list[StudentIndexOut])
def get_index_history(student_id: int, db: Session = Depends(get_db)):
    return StudentIndexService(db).get_history_for_student(student_id)