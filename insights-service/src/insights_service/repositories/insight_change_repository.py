from sqlalchemy import select
from sqlalchemy.orm import Session

from insights_service.models.enums import ChangeDirection
from insights_service.models.insight_change import InsightChange
from insights_service.models.insight_run import InsightRun


class InsightChangeRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_run(
        self,
        run_id: int,
        direction: ChangeDirection | None = None,
        group_ids: list[int] | None = None,
    ) -> list[InsightChange]:
        query = select(InsightChange).where(InsightChange.run_id == run_id)
        if direction is not None:
            query = query.where(InsightChange.direction == direction)
        if group_ids is not None:
            query = query.where(InsightChange.group_id.in_(group_ids))
        return list(self.session.scalars(query.order_by(InsightChange.student_id, InsightChange.id)).all())

    def get_for_student(self, student_id: int, limit: int) -> list[InsightChange]:
        return list(self.session.scalars(
            select(InsightChange)
            .join(InsightRun, InsightRun.id == InsightChange.run_id)
            .where(InsightChange.student_id == student_id)
            .order_by(InsightRun.created_at.desc(), InsightChange.id)
            .limit(limit)
        ).all())
