from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ml_service.database import get_db
from ml_service.ml.training.training_service import TrainingService

router = APIRouter(prefix="/training", tags=["training"])


@router.post("/train")
def trigger_training(db: Session = Depends(get_db)):
    try:
        service = TrainingService(db)
        results = service.train_all_models()
        return {
            "status": "ok",
            "trained_models": {
                key: {
                    "model_version_id": result.version.id,
                    "version_label": result.version.version_label,
                    "purpose": result.version.purpose.value,
                    "metrics": result.version.metrics,
                    "promoted": result.promoted,
                    "warning": result.warning,
                }
                for key, result in results.items()
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))