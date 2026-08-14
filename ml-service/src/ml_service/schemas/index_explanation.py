from pydantic import BaseModel, ConfigDict


class IndexExplanationCreate(BaseModel):
    feature_name: str
    feature_value: float
    shap_value: float
    rank: int


class IndexExplanationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_index_id: int
    feature_name: str
    feature_value: float
    shap_value: float
    rank: int