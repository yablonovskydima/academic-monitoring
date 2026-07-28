from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from import_service.database import get_db
from import_service.services.student_features_service import StudentFeaturesService
from import_service.schemas.student_features import StudentFeaturesRaw

router = APIRouter(prefix="/student-features", tags=["student_features"])


@router.get("/", response_model=list[StudentFeaturesRaw])
def get_all_student_features(db: Session = Depends(get_db)):
    return StudentFeaturesService(db).get_all_features()