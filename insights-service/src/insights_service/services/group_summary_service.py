from sqlalchemy.orm import Session

from insights_service.repositories.group_summary_repository import GroupSummaryRepository
from insights_service.repositories.insight_run_repository import InsightRunRepository
from insights_service.schemas.group_summary import CurrentGroupSummariesOut, GroupSummaryOut
from insights_service.schemas.insight_run import InsightRunOut


class GroupSummaryService:
    def __init__(self, db: Session):
        self.runs = InsightRunRepository(db)
        self.summaries = GroupSummaryRepository(db)

    def get_for_run(self, run_id: int, group_ids: list[int] | None = None) -> list[GroupSummaryOut]:
        return [GroupSummaryOut.model_validate(summary) for summary in self.summaries.get_by_run(run_id, group_ids)]

    def get_latest(self, group_ids: list[int] | None = None) -> CurrentGroupSummariesOut:
        latest_run = self.runs.get_latest()
        if latest_run is None:
            return CurrentGroupSummariesOut(run=None, items=[])
        return CurrentGroupSummariesOut(
            run=InsightRunOut.model_validate(latest_run),
            items=self.get_for_run(latest_run.id, group_ids),
        )
