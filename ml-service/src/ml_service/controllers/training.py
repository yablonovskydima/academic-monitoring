from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ml_service.database import get_db
from ml_service.ml.training.training_service import TrainingService

router = APIRouter(prefix="/training", tags=["training"])


@router.post("/train")
def trigger_training(version_label: str, db: Session = Depends(get_db)):
    try:
        service = TrainingService(db)
        results = service.train_all_models(version_label)
        return {
            "status": "ok",
            "trained_models": {
                key: {
                    "model_version_id": version.id,
                    "purpose": version.purpose.value,
                    "metrics": version.metrics,
                }
                for key, version in results.items()
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))