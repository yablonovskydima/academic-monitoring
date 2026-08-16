from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ml_service.database import get_db
from ml_service.services.model_version_service import ModelVersionService
from ml_service.schemas.model_version import ModelVersionOut

router = APIRouter(prefix="/model-versions", tags=["model_versions"])


@router.get("/", response_model=list[ModelVersionOut])
def get_all_model_versions(db: Session = Depends(get_db)):
    return ModelVersionService(db).get_all()