from sqlalchemy import select
from sqlalchemy.orm import Session

from ml_service.models.ml_job import ACTIVE_JOB_STATUSES, MLJob, MLJobType


class MLJobRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, job_id: int) -> MLJob | None:
        return self.session.get(MLJob, job_id)

    def get_latest_by_type(self, job_type: MLJobType) -> MLJob | None:
        return self.session.scalars(
            select(MLJob)
            .where(MLJob.job_type == job_type)
            .order_by(MLJob.created_at.desc(), MLJob.id.desc())
        ).first()

    def get_active_by_type(self, job_type: MLJobType) -> MLJob | None:
        return self.session.scalars(
            select(MLJob).where(MLJob.job_type == job_type, MLJob.status.in_(ACTIVE_JOB_STATUSES))
        ).first()

    def get_all_active(self) -> list[MLJob]:
        return list(self.session.scalars(
            select(MLJob).where(MLJob.status.in_(ACTIVE_JOB_STATUSES))
        ).all())

    def save(self, job: MLJob) -> MLJob:
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job
