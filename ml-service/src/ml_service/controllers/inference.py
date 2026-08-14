from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ml_service.database import get_db
from ml_service.ml.inference.inference_service import InferenceService

router = APIRouter(prefix="/inference", tags=["inference"])


@router.post("/predict-all")
def trigger_inference(db: Session = Depends(get_db)):
    try:
        service = InferenceService(db)
        processed_count = service.calculate_all_indexes()
        return {"status": "ok", "processed": processed_count}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))