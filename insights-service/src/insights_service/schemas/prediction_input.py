from typing import Any

from pydantic import BaseModel, Field, model_validator

from insights_service.models.enums import IndexCategory, RiskType


class ContributionIn(BaseModel):
    feature_name: str
    feature_value: float
    shap_value: float


class RiskPredictionIn(BaseModel):
    risk_type: RiskType
    probability: float = Field(ge=0.0, le=1.0)
    contributions: list[ContributionIn] = []


class ForecastIn(BaseModel):
    semesters_ahead: int = Field(ge=1)
    predicted_index_value: float


class StudentPredictionIn(BaseModel):
    student_id: int
    group_id: int
    semester_id: int
    student_index_id: int | None = None
    index_value: float
    index_category: IndexCategory
    features: dict[str, Any] = {}
    index_contributions: list[ContributionIn] = []
    risks: list[RiskPredictionIn] = []
    forecasts: list[ForecastIn] = []

    @model_validator(mode="after")
    def _one_prediction_per_risk_type_and_horizon(self) -> "StudentPredictionIn":
        risk_types = [risk.risk_type for risk in self.risks]
        if len(risk_types) != len(set(risk_types)):
            raise ValueError(f"student {self.student_id} has more than one prediction for a risk type")
        horizons = [forecast.semesters_ahead for forecast in self.forecasts]
        if len(horizons) != len(set(horizons)):
            raise ValueError(f"student {self.student_id} has more than one forecast for a horizon")
        return self


class InsightRunCreate(BaseModel):
    source_job_id: int | None = None
    predictions: list[StudentPredictionIn] = Field(min_length=1)

    @model_validator(mode="after")
    def _one_prediction_per_student(self) -> "InsightRunCreate":
        student_ids = [prediction.student_id for prediction in self.predictions]
        if len(student_ids) != len(set(student_ids)):
            raise ValueError("a run must contain at most one prediction per student")
        return self
