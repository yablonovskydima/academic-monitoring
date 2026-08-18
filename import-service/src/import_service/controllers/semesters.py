import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from import_service.database import get_db
from import_service.services.semester_service import SemesterService
from import_service.schemas.semester import SemesterOut

router = APIRouter(prefix="/semesters", tags=["semesters"])
logger = logging.getLogger(__name__)


@router.get("/", response_model=list[SemesterOut])
def get_semesters(db: Session = Depends(get_db)):
    return SemesterService(db).get_all()


@router.get("/current", response_model=SemesterOut)
def get_current_semester(db: Session = Depends(get_db)):
    semester = SemesterService(db).get_current()

    if semester is None:
        logger.info(
            "No active semester found. This may indicate an academic break."
        )
        raise HTTPException(
            status_code=404,
            detail="No active semester found. It may currently be an academic break.",
        )

    return semester


@router.get("/latest-with-data", response_model=SemesterOut)
def get_latest_semester_with_data(db: Session = Depends(get_db)):
    semester = SemesterService(db).get_latest_with_data()

    if semester is None:
        raise HTTPException(
            status_code=404,
            detail="No semester with data found",
        )

    return semester

@router.get("/{semester_id}", response_model=SemesterOut)
def get_semester(semester_id: int, db: Session = Depends(get_db)):
    semester = SemesterService(db).get_by_id(semester_id)
    if semester is None:
        raise HTTPException(status_code=404, detail="Semester not found")
    return semester