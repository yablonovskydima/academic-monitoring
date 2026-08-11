from datetime import datetime

from pydantic import BaseModel, ConfigDict

from ml_service.models.student_index import IndexCategory
from ml_service.schemas.index_explanation import IndexExplanationOut
from ml_service.schemas.feature_snapshot import FeatureSnapshotOut
from ml_service.schemas.risk_assessment import RiskAssessmentOut


class StudentIndexCreate(BaseModel):
    student_id: int
    semester_id: int
    model_version_id: int
    index_value: float
    category: IndexCategory
    calculated_at: datetime


class StudentIndexOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    semester_id: int
    model_version_id: int
    index_value: float
    category: IndexCategory
    calculated_at: datetime


class StudentIndexFull(StudentIndexOut):
    explanations: list[IndexExplanationOut] = []
    feature_snapshot: FeatureSnapshotOut | None = None
    risk_assessments: list[RiskAssessmentOut] = []