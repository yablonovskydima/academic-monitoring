from datetime import datetime

from pydantic import BaseModel, ConfigDict

from insights_service.models.enums import (
    IndexCategory, InsightTarget, ReasonDirection, ReasonStrength, RiskKind, RiskLevel, RiskType, Theme,
)
from insights_service.models.student_insight import StudentInsight
from insights_service.schemas.insight_run import InsightRunOut


class InsightReasonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    target: InsightTarget
    theme: Theme
    title: str
    direction: ReasonDirection
    strength: ReasonStrength
    text: str
    action: str | None
    feature_name: str
    feature_value: float
    percentile: int | None
    rank: int


class ForecastOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    semesters_ahead: int
    predicted_index_value: float


class RiskInsightOut(BaseModel):
    risk_type: RiskType
    kind: RiskKind
    level: RiskLevel
    probability: float
    reasons: list[InsightReasonOut]


class StudentInsightSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    student_id: int
    group_id: int
    semester_id: int
    index_value: float
    index_category: IndexCategory
    headline: str
    is_current: bool

    @classmethod
    def from_summary_model(cls, insight: StudentInsight, is_current: bool) -> "StudentInsightSummaryOut":
        return cls(
            id=insight.id,
            run_id=insight.run_id,
            student_id=insight.student_id,
            group_id=insight.group_id,
            semester_id=insight.semester_id,
            index_value=insight.index_value,
            index_category=insight.index_category,
            headline=insight.headline,
            is_current=is_current,
        )


class RiskLevelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    risk_type: RiskType
    kind: RiskKind
    level: RiskLevel


class StudentInsightListItemOut(StudentInsightSummaryOut):
    risks: list[RiskLevelOut]

    @classmethod
    def from_list_model(cls, insight: StudentInsight) -> "StudentInsightListItemOut":
        summary = StudentInsightSummaryOut.from_summary_model(insight, is_current=True)
        return cls(
            **summary.model_dump(),
            risks=[
                RiskLevelOut.model_validate(risk)
                for risk in sorted(insight.risks, key=lambda r: list(RiskType).index(r.risk_type))
            ],
        )


class CurrentStudentInsightsOut(BaseModel):
    run: InsightRunOut | None
    total: int
    items: list[StudentInsightListItemOut]


class StudentInsightOut(StudentInsightSummaryOut):
    student_index_id: int | None
    created_at: datetime
    index_reasons: list[InsightReasonOut]
    risks: list[RiskInsightOut]
    forecasts: list[ForecastOut]

    @classmethod
    def from_model(cls, insight: StudentInsight, is_current: bool) -> "StudentInsightOut":
        reasons_by_target: dict[InsightTarget, list[InsightReasonOut]] = {}
        for reason in insight.reasons:
            reasons_by_target.setdefault(reason.target, []).append(InsightReasonOut.model_validate(reason))

        return cls(
            id=insight.id,
            run_id=insight.run_id,
            student_id=insight.student_id,
            group_id=insight.group_id,
            semester_id=insight.semester_id,
            student_index_id=insight.student_index_id,
            index_value=insight.index_value,
            index_category=insight.index_category,
            headline=insight.headline,
            is_current=is_current,
            created_at=insight.run.created_at,
            index_reasons=reasons_by_target.get(InsightTarget.index, []),
            risks=[
                RiskInsightOut(
                    risk_type=risk.risk_type,
                    kind=risk.kind,
                    level=risk.level,
                    probability=risk.probability,
                    reasons=reasons_by_target.get(InsightTarget(risk.risk_type.value), []),
                )
                for risk in sorted(insight.risks, key=lambda r: list(RiskType).index(r.risk_type))
            ],
            forecasts=[ForecastOut.model_validate(forecast) for forecast in insight.forecasts],
        )
