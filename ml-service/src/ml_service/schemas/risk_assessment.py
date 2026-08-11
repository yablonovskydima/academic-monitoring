from pydantic import BaseModel, ConfigDict

from ml_service.models.risk_assessment import RiskType


class RiskAssessmentCreate(BaseModel):
    risk_type: RiskType
    probability: float
    model_version_id: int


class RiskAssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_index_id: int
    risk_type: RiskType
    probability: float
    model_version_id: int