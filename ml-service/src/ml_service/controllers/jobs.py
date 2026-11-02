from fastapi import APIRouter, Depends, HTTPException, status

from ml_service.models.ml_job import MLJobType
from ml_service.schemas.ml_job import MLJobCreate, MLJobOut
from ml_service.services.ml_job_service import JobAlreadyActive, MLJobService


def get_job_service() -> MLJobService:
    return MLJobService()


def make_job_router(prefix: str, job_type: MLJobType) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[job_type.value])

    @router.post("/jobs", response_model=MLJobOut, status_code=status.HTTP_202_ACCEPTED)
    def submit_job(data: MLJobCreate | None = None, service: MLJobService = Depends(get_job_service)):
        try:
            return service.submit(job_type, requested_by=data.requested_by if data else None)
        except JobAlreadyActive as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": str(e), "job": e.job.model_dump(mode="json")},
            )

    @router.get("/jobs/latest", response_model=MLJobOut)
    def get_latest_job(service: MLJobService = Depends(get_job_service)):
        job = service.latest(job_type)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No {job_type.value} jobs yet")
        return job

    @router.get("/jobs/{job_id}", response_model=MLJobOut)
    def get_job(job_id: int, service: MLJobService = Depends(get_job_service)):
        job = service.get(job_type, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{job_type.value} job not found")
        return job

    return router
