from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from import_service.database import get_db
from import_service.services.subject_service import SubjectService
from import_service.schemas.subject import SubjectOut

router = APIRouter(prefix="/subjects", tags=["subjects"])


@router.get("/", response_model=list[SubjectOut])
def get_subjects(db: Session = Depends(get_db)):
    return SubjectService(db).get_all()


@router.get("/{subject_id}", response_model=SubjectOut)
def get_subject(subject_id: int, db: Session = Depends(get_db)):
    subject = SubjectService(db).get_by_id(subject_id)
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject