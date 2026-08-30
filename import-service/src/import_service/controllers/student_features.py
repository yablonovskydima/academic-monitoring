from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from import_service.database import get_db
from import_service.schemas.student_semester_features import StudentSemesterFeatures
from import_service.services.student_semester_features_service import StudentSemesterFeaturesService

router = APIRouter(prefix="/student-features", tags=["student_features"])


@router.get("/by-semester", response_model=list[StudentSemesterFeatures])
def get_all_student_semester_features(limit: int = 1000, offset: int = 0, db: Session = Depends(get_db)):
    return StudentSemesterFeaturesService(db).get_all(limit=limit, offset=offset)
