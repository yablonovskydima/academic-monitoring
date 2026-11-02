from pydantic import BaseModel, ConfigDict


class RiskExplanationCreate(BaseModel):
    feature_name: str
    feature_value: float
    shap_value: float
    rank: int


class RiskExplanationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    risk_assessment_id: int
    feature_name: str
    feature_value: float
    shap_value: float
    rank: int
