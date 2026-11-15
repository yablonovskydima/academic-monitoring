from sqlalchemy import select
from sqlalchemy.orm import Session

from insights_service.models.group_summary import GroupSummary


class GroupSummaryRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_run(self, run_id: int, group_ids: list[int] | None = None) -> list[GroupSummary]:
        query = select(GroupSummary).where(GroupSummary.run_id == run_id)
        if group_ids is not None:
            query = query.where(GroupSummary.group_id.in_(group_ids))
        return list(self.session.scalars(query.order_by(GroupSummary.group_id)).all())
