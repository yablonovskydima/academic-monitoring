from sqlalchemy.orm import Session

from insights_service.repositories.insight_run_repository import InsightRunRepository
from insights_service.repositories.student_insight_repository import StudentInsightRepository
from insights_service.schemas.insight_run import InsightRunOut
from insights_service.schemas.student_insight import (
    CurrentStudentInsightsOut, StudentInsightListItemOut, StudentInsightOut, StudentInsightSummaryOut,
)

DEFAULT_HISTORY_LIMIT = 20
DEFAULT_PAGE_SIZE = 50


class StudentInsightService:
    def __init__(self, db: Session):
        self.runs = InsightRunRepository(db)
        self.students = StudentInsightRepository(db)

    def get_latest(self, student_id: int) -> StudentInsightOut | None:
        insight = self.students.get_latest_for_student(student_id)
        if insight is None:
            return None
        return StudentInsightOut.from_model(insight, is_current=insight.run_id == self._latest_run_id())

    def get_history(self, student_id: int, limit: int = DEFAULT_HISTORY_LIMIT) -> list[StudentInsightSummaryOut]:
        latest_run_id = self._latest_run_id()
        return [
            StudentInsightSummaryOut.from_summary_model(insight, is_current=insight.run_id == latest_run_id)
            for insight in self.students.get_history_for_student(student_id, limit)
        ]

    def search_current(
        self,
        group_ids: list[int] | None = None,
        student_ids: list[int] | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> CurrentStudentInsightsOut:
        latest_run = self.runs.get_latest()
        if latest_run is None:
            return CurrentStudentInsightsOut(run=None, total=0, items=[])

        items, total = self.students.search_in_run(latest_run.id, group_ids, student_ids, limit, offset)
        return CurrentStudentInsightsOut(
            run=InsightRunOut.model_validate(latest_run),
            total=total,
            items=[StudentInsightListItemOut.from_list_model(insight) for insight in items],
        )

    def _latest_run_id(self) -> int | None:
        latest_run = self.runs.get_latest()
        return latest_run.id if latest_run is not None else None
