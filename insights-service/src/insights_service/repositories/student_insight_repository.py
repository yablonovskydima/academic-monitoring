from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from insights_service.models.insight_run import InsightRun
from insights_service.models.student_insight import StudentInsight


def _with_details():
    return (
        selectinload(StudentInsight.risks),
        selectinload(StudentInsight.reasons),
        selectinload(StudentInsight.forecasts),
        selectinload(StudentInsight.run),
    )


class StudentInsightRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_latest_for_student(self, student_id: int) -> StudentInsight | None:
        return self.session.scalars(
            select(StudentInsight)
            .options(*_with_details())
            .join(InsightRun, InsightRun.id == StudentInsight.run_id)
            .where(StudentInsight.student_id == student_id)
            .order_by(InsightRun.created_at.desc(), InsightRun.id.desc())
        ).first()

    def get_history_for_student(self, student_id: int, limit: int) -> list[StudentInsight]:
        return list(self.session.scalars(
            select(StudentInsight)
            .join(InsightRun, InsightRun.id == StudentInsight.run_id)
            .where(StudentInsight.student_id == student_id)
            .order_by(InsightRun.created_at.desc(), InsightRun.id.desc())
            .limit(limit)
        ).all())

    def get_by_run(self, run_id: int) -> list[StudentInsight]:
        return list(self.session.scalars(
            select(StudentInsight)
            .options(selectinload(StudentInsight.risks))
            .where(StudentInsight.run_id == run_id)
        ).all())

    def search_in_run(
        self,
        run_id: int,
        group_ids: list[int] | None,
        student_ids: list[int] | None,
        limit: int,
        offset: int,
    ) -> tuple[list[StudentInsight], int]:
        query = select(StudentInsight).where(StudentInsight.run_id == run_id)
        if group_ids is not None:
            query = query.where(StudentInsight.group_id.in_(group_ids))
        if student_ids is not None:
            query = query.where(StudentInsight.student_id.in_(student_ids))

        total = self.session.scalar(select(func.count()).select_from(query.subquery()))
        items = self.session.scalars(
            query
            .options(selectinload(StudentInsight.risks))
            .order_by(StudentInsight.index_value, StudentInsight.student_id)
            .limit(limit)
            .offset(offset)
        ).all()
        return list(items), total
