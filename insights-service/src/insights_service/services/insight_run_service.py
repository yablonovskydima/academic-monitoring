from dataclasses import asdict

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from insights_service.insights.changes import StudentState, detect_changes
from insights_service.insights.cohort import Cohort
from insights_service.insights.group_summaries import StudentOutcome, summarize_groups
from insights_service.insights.headlines import RiskDraft, compose_headline
from insights_service.insights.reasons import ReasonDraft, build_reasons
from insights_service.insights.risk_levels import assess_admission, supported_level
from insights_service.models.enums import ChangeDirection, InsightTarget, RiskKind, RiskType
from insights_service.models.group_summary import GroupSummary
from insights_service.models.insight_change import InsightChange
from insights_service.models.insight_forecast import InsightForecast
from insights_service.models.insight_reason import InsightReason
from insights_service.models.insight_run import InsightRun
from insights_service.models.risk_insight import RiskInsight
from insights_service.models.student_insight import StudentInsight
from insights_service.repositories.insight_run_repository import InsightRunRepository
from insights_service.repositories.student_insight_repository import StudentInsightRepository
from insights_service.schemas.insight_run import InsightRunOut
from insights_service.schemas.prediction_input import InsightRunCreate, RiskPredictionIn, StudentPredictionIn
from insights_service.utils.clock import utc_now


class InsightRunService:
    def __init__(self, db: Session):
        self.runs = InsightRunRepository(db)
        self.students = StudentInsightRepository(db)

    def get(self, run_id: int) -> InsightRunOut | None:
        run = self.runs.get_by_id(run_id)
        return InsightRunOut.model_validate(run) if run is not None else None

    def get_latest(self) -> InsightRunOut | None:
        run = self.runs.get_latest()
        return InsightRunOut.model_validate(run) if run is not None else None

    def get_by_source_job_id(self, source_job_id: int) -> InsightRunOut | None:
        run = self.runs.get_by_source_job_id(source_job_id)
        return InsightRunOut.model_validate(run) if run is not None else None

    def process_run(self, data: InsightRunCreate) -> InsightRunOut:
        if data.source_job_id is not None:
            existing = self.get_by_source_job_id(data.source_job_id)
            if existing is not None:
                return existing

        previous_run = self.runs.get_latest()
        previous_states = (
            {insight.student_id: _state_of(insight) for insight in self.students.get_by_run(previous_run.id)}
            if previous_run is not None else {}
        )

        cohort = Cohort(prediction.features for prediction in data.predictions)
        run = InsightRun(
            source_job_id=data.source_job_id,
            semester_id=max(prediction.semester_id for prediction in data.predictions),
            students_count=len(data.predictions),
            created_at=utc_now(),
        )

        outcomes: list[StudentOutcome] = []
        worsened_student_ids: set[int] = set()

        for prediction in data.predictions:
            insight, outcome = self._build_student(prediction, cohort)
            run.student_insights.append(insight)
            outcomes.append(outcome)

            previous = previous_states.get(prediction.student_id)
            if previous is None:
                continue

            for change in detect_changes(previous, outcome.state):
                run.changes.append(InsightChange(
                    previous_run_id=previous_run.id,
                    student_id=prediction.student_id,
                    group_id=prediction.group_id,
                    **asdict(change),
                ))
                if change.direction is ChangeDirection.worsened:
                    worsened_student_ids.add(prediction.student_id)

        for summary in summarize_groups(outcomes, worsened_student_ids):
            run.group_summaries.append(GroupSummary(**asdict(summary)))

        try:
            return InsightRunOut.model_validate(self.runs.save(run))
        except IntegrityError:
            self.runs.rollback()
            existing = self.get_by_source_job_id(data.source_job_id) if data.source_job_id is not None else None
            if existing is None:
                raise
            return existing

    def _build_student(
        self, prediction: StudentPredictionIn, cohort: Cohort,
    ) -> tuple[StudentInsight, StudentOutcome]:
        index_reasons = build_reasons(prediction.index_contributions, cohort, higher_output_is_worse=False)
        risks = [_assess_risk(risk, prediction.features, cohort) for risk in prediction.risks]
        headline = compose_headline(prediction.index_category, index_reasons, risks)

        insight = StudentInsight(
            student_id=prediction.student_id,
            group_id=prediction.group_id,
            semester_id=prediction.semester_id,
            student_index_id=prediction.student_index_id,
            index_value=prediction.index_value,
            index_category=prediction.index_category,
            headline=headline.text,
            risks=[
                RiskInsight(risk_type=risk.risk_type, kind=risk.kind, level=risk.level, probability=risk.probability)
                for risk in risks
            ],
            reasons=_reason_models(InsightTarget.index, index_reasons) + [
                reason
                for risk in risks
                for reason in _reason_models(InsightTarget(risk.risk_type.value), risk.reasons)
            ],
            forecasts=[
                InsightForecast(
                    semesters_ahead=forecast.semesters_ahead,
                    predicted_index_value=forecast.predicted_index_value,
                )
                for forecast in prediction.forecasts
            ],
        )

        outcome = StudentOutcome(
            student_id=prediction.student_id,
            group_id=prediction.group_id,
            state=StudentState(prediction.index_category, {risk.risk_type: risk.level for risk in risks}),
            needs_attention=headline.needs_attention,
            main_theme=headline.theme,
        )
        return insight, outcome


def _assess_risk(risk: RiskPredictionIn, features: dict, cohort: Cohort) -> RiskDraft:
    if risk.risk_type is RiskType.exam_admission_denial:
        by_rule = assess_admission(features)
        if by_rule is not None:
            level, reasons = by_rule
            return RiskDraft(risk.risk_type, RiskKind.status, level, risk.probability, reasons)
        kind = RiskKind.status
    else:
        kind = RiskKind.forecast

    reasons = build_reasons(risk.contributions, cohort, higher_output_is_worse=True)
    return RiskDraft(risk.risk_type, kind, supported_level(risk.probability, reasons), risk.probability, reasons)


def _reason_models(target: InsightTarget, reasons: list[ReasonDraft]) -> list[InsightReason]:
    return [InsightReason(target=target, rank=rank, **asdict(reason)) for rank, reason in enumerate(reasons, start=1)]


def _state_of(insight: StudentInsight) -> StudentState:
    return StudentState(insight.index_category, {risk.risk_type: risk.level for risk in insight.risks})
