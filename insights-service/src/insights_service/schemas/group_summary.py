from pydantic import BaseModel, ConfigDict

from insights_service.models.enums import Theme
from insights_service.schemas.insight_run import InsightRunOut


class GroupSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: int
    group_id: int
    students_count: int
    index_high_count: int
    index_medium_count: int
    index_low_count: int
    expulsion_high_count: int
    debt_high_count: int
    admission_denied_count: int
    attention_count: int
    worsened_count: int
    top_theme: Theme | None


class CurrentGroupSummariesOut(BaseModel):
    run: InsightRunOut | None
    items: list[GroupSummaryOut]
