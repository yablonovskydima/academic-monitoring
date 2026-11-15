from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from insights_service.database import get_db
from insights_service.schemas.insight_run import InsightRunOut
from insights_service.schemas.prediction_input import InsightRunCreate
from insights_service.services.insight_run_service import InsightRunService

router = APIRouter(prefix="/insight-runs", tags=["insight_runs"])


@router.post("/", response_model=InsightRunOut, status_code=status.HTTP_201_CREATED)
def submit_run(data: InsightRunCreate, response: Response, db: Session = Depends(get_db)):
    service = InsightRunService(db)

    if data.source_job_id is not None:
        existing = service.get_by_source_job_id(data.source_job_id)
        if existing is not None:
            response.status_code = status.HTTP_200_OK
            return existing

    return service.process_run(data)


@router.get("/latest", response_model=InsightRunOut)
def get_latest_run(db: Session = Depends(get_db)):
    run = InsightRunService(db).get_latest()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No insight runs yet")
    return run


@router.get("/{run_id}", response_model=InsightRunOut)
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = InsightRunService(db).get(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insight run not found")
    return run
