from insights_service.models.enums import IndexCategory, RiskType
from insights_service.schemas.prediction_input import (
    ContributionIn, ForecastIn, RiskPredictionIn, StudentPredictionIn,
)

TYPICAL_FEATURES = dict(
    study_mode="full_time",
    avg_grade=75.0,
    cumulative_avg_grade=75.0,
    grade_stddev=15.0,
    lecture_absence_percent=12.0,
    lab_absence_percent=12.0,
    absence_percent=12.0,
    unworked_absences_count=5,
    cumulative_absence_percent=12.0,
    missing_submissions_count=2,
    late_submissions_count=8,
    cumulative_avg_missing_submissions=2.0,
    cumulative_avg_late_submissions=8.0,
    avg_grade_delta=0.0,
    absence_percent_delta=0.0,
    missing_submissions_delta=0,
    course_year=2,
    semesters_completed_count=3,
)


def contribution(name: str, value: float, shap: float) -> ContributionIn:
    return ContributionIn(feature_name=name, feature_value=value, shap_value=shap)


def risk(risk_type: RiskType, probability: float, *contributions: ContributionIn) -> RiskPredictionIn:
    return RiskPredictionIn(risk_type=risk_type, probability=probability, contributions=list(contributions))


def prediction(
    student_id: int,
    group_id: int = 1,
    index_category: IndexCategory = IndexCategory.high,
    index_value: float = 80.0,
    index_contributions: list[ContributionIn] | None = None,
    risks: list[RiskPredictionIn] | None = None,
    forecasts: list[ForecastIn] | None = None,
    **feature_overrides,
) -> StudentPredictionIn:
    return StudentPredictionIn(
        student_id=student_id,
        group_id=group_id,
        semester_id=6,
        student_index_id=1000 + student_id,
        index_value=index_value,
        index_category=index_category,
        features={**TYPICAL_FEATURES, **feature_overrides},
        index_contributions=index_contributions or [],
        risks=risks if risks is not None else [
            risk(RiskType.expulsion, 0.1),
            risk(RiskType.academic_debt, 0.1),
            risk(RiskType.exam_admission_denial, 0.0),
        ],
        forecasts=forecasts or [],
    )


def forecast(semesters_ahead: int, value: float) -> ForecastIn:
    return ForecastIn(semesters_ahead=semesters_ahead, predicted_index_value=value)
