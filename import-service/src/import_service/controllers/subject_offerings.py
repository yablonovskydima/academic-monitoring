from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from import_service.database import get_db
from import_service.services.subject_offering_service import SubjectOfferingService
from import_service.schemas.subject_offering import SubjectOfferingOut, SubjectOfferingFull

router = APIRouter(prefix="/subject-offerings", tags=["subject_offerings"])


@router.get("/", response_model=list[SubjectOfferingOut])
def get_subject_offerings(db: Session = Depends(get_db)):
    return SubjectOfferingService(db).get_all()


@router.get("/{offering_id}", response_model=SubjectOfferingOut)
def get_subject_offering(offering_id: int, db: Session = Depends(get_db)):
    offering = SubjectOfferingService(db).get_by_id(offering_id)
    if offering is None:
        raise HTTPException(status_code=404, detail="Subject offering not found")
    return offering


@router.get("/{offering_id}/full", response_model=SubjectOfferingFull)
def get_subject_offering_full(offering_id: int, db: Session = Depends(get_db)):
    offering = SubjectOfferingService(db).get_full(offering_id)
    if offering is None:
        raise HTTPException(status_code=404, detail="Subject offering not found")
    return offering


@router.get("/by-semester/{semester_id}", response_model=list[SubjectOfferingOut])
def get_offerings_by_semester(semester_id: int, db: Session = Depends(get_db)):
    return SubjectOfferingService(db).get_by_semester(semester_id)