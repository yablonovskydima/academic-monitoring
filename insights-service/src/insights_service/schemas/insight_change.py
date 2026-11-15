from pydantic import BaseModel, ConfigDict

from insights_service.models.enums import ChangeDirection, ChangeKind, RiskType
from insights_service.schemas.insight_run import InsightRunOut


class InsightChangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    previous_run_id: int
    student_id: int
    group_id: int
    kind: ChangeKind
    risk_type: RiskType | None
    from_value: str
    to_value: str
    direction: ChangeDirection
    text: str


class CurrentInsightChangesOut(BaseModel):
    run: InsightRunOut | None
    items: list[InsightChangeOut]
