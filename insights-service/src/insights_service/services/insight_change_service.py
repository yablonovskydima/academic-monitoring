from sqlalchemy.orm import Session

from insights_service.models.enums import ChangeDirection
from insights_service.repositories.insight_change_repository import InsightChangeRepository
from insights_service.repositories.insight_run_repository import InsightRunRepository
from insights_service.schemas.insight_change import CurrentInsightChangesOut, InsightChangeOut
from insights_service.schemas.insight_run import InsightRunOut

DEFAULT_STUDENT_LIMIT = 50


class InsightChangeService:
    def __init__(self, db: Session):
        self.runs = InsightRunRepository(db)
        self.changes = InsightChangeRepository(db)

    def get_for_run(
        self, run_id: int, worsened_only: bool = False, group_ids: list[int] | None = None,
    ) -> list[InsightChangeOut]:
        direction = ChangeDirection.worsened if worsened_only else None
        return [
            InsightChangeOut.model_validate(change)
            for change in self.changes.get_by_run(run_id, direction, group_ids)
        ]

    def get_latest(self, worsened_only: bool = False, group_ids: list[int] | None = None) -> CurrentInsightChangesOut:
        latest_run = self.runs.get_latest()
        if latest_run is None:
            return CurrentInsightChangesOut(run=None, items=[])
        return CurrentInsightChangesOut(
            run=InsightRunOut.model_validate(latest_run),
            items=self.get_for_run(latest_run.id, worsened_only, group_ids),
        )

    def get_for_student(self, student_id: int, limit: int = DEFAULT_STUDENT_LIMIT) -> list[InsightChangeOut]:
        return [InsightChangeOut.model_validate(change) for change in self.changes.get_for_student(student_id, limit)]
