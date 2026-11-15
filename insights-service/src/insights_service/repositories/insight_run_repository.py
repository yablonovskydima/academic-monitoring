from sqlalchemy import select
from sqlalchemy.orm import Session

from insights_service.models.insight_run import InsightRun


class InsightRunRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, run_id: int) -> InsightRun | None:
        return self.session.get(InsightRun, run_id)

    def get_by_source_job_id(self, source_job_id: int) -> InsightRun | None:
        return self.session.scalars(
            select(InsightRun).where(InsightRun.source_job_id == source_job_id)
        ).first()

    def get_latest(self) -> InsightRun | None:
        return self.session.scalars(
            select(InsightRun).order_by(InsightRun.created_at.desc(), InsightRun.id.desc())
        ).first()

    def save(self, run: InsightRun) -> InsightRun:
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def rollback(self) -> None:
        self.session.rollback()
