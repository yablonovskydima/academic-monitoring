from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from import_service.database import get_db
from import_service.services.faculty_service import FacultyService
from import_service.schemas.faculty import FacultyOut, FacultyFull

router = APIRouter(prefix="/faculties", tags=["faculties"])


@router.get("/", response_model=list[FacultyOut])
def get_faculties(db: Session = Depends(get_db)):
    return FacultyService(db).get_all()


@router.get("/{faculty_id}", response_model=FacultyOut)
def get_faculty(faculty_id: int, db: Session = Depends(get_db)):
    faculty = FacultyService(db).get_by_id(faculty_id)
    if faculty is None:
        raise HTTPException(status_code=404, detail="Faculty not found")
    return faculty


@router.get("/{faculty_id}/full", response_model=FacultyFull)
def get_faculty_full(faculty_id: int, db: Session = Depends(get_db)):
    faculty = FacultyService(db).get_full(faculty_id)
    if faculty is None:
        raise HTTPException(status_code=404, detail="Faculty not found")
    return faculty
